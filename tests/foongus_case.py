#!/usr/bin/env python3
"""READ-ONLY release-simulation regression for Foongus/Amoonguss, not a production release.

247 baseline is synthesized by removing precisely the two from the published 249.
Test-only trust anchors are derived from that frozen reference and are NEVER
copied back to main or a production kit. Real importer proofs are obtained
separately by scripts/run_pinned_import_e2e.py in the same run.
"""
from __future__ import annotations
import argparse, csv, hashlib, io, json, re, shutil, subprocess, sys, tempfile, threading, zipfile, struct, zlib
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
ROOT = Path(__file__).resolve().parents[1]
ADDED = ('Foongus','Amoonguss')
JA = {'Foongus':'タマゲタケ','Amoonguss':'モロバレル'}
KEEP_KEYS=('app.js','index.html','styles.css','sw.js','zip-store.js','ui-extras.js','update-status.js','update-status.json','manifest.webmanifest')
def raw_json(x): return (json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(x):return sha(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def need(c,msg):
    if not c:raise AssertionError(msg)
def pin_line(src,name,original,new):
    pat=r'(?m)^('+re.escape(name)+r'\s*=\s*)'+original+r'$'
    out,n=re.subn(pat,lambda m:m.group(1)+new,src)
    need(n==1,'TRUST_ANCHOR_PATTERN_MISSING: '+name)
    return out

def independent_kit_verify(kit):
    code=('import pathlib,sys,json;sys.path.insert(0,sys.argv[1]);'
          'from SPECIES_AUDIT import verify_bundle;'
          'm,v=verify_bundle(pathlib.Path(sys.argv[1]));print(len(m["pokemon"]))')
    p=subprocess.run([sys.executable,'-c',code,str(kit)],capture_output=True,text=True,timeout=35)
    need(p.returncode==0,'SPECIES_AUDIT H O L D: '+p.stderr[-1600:])
    return int(p.stdout.strip())

def prepare(src,dst,report):
    src,dst=Path(src),Path(dst)
    need(not dst.exists(),'Destination must be new isolated directory')
    dst.mkdir(parents=True)
    for n in KEEP_KEYS:
        if (src/n).is_file():shutil.copy2(src/n,dst/n)
    shutil.copytree(src/'kit-assets',dst/'kit-assets',ignore=shutil.ignore_patterns('__pycache__'))
    original=read(src/'kit-assets/MASTER_DATA.json'); old=read(dst/'kit-assets/MASTER_DATA.json')
    need(original==old,'Source fixture mismatch')
    all_en=[p['name_en'] for p in old['pokemon']]
    need(len(all_en)==249 and all(all_en.count(x)==1 for x in ADDED),'EXPECTED_EXACT_249_REFERENCE_WITH_TWO_TARGETS')
    old['pokemon']=[p for p in old['pokemon'] if p['name_en'] not in ADDED]
    need(len(old['pokemon'])==247,'EXPECTED_247_BASE')
    master_path=dst/'kit-assets/MASTER_DATA.json'; master_path.write_bytes(raw_json(old))
    base_master_sha=sha(master_path.read_bytes())
    ver_path=dst/'kit-assets/KIT_VERSION.json';v=read(ver_path)
    code_path=dst/'kit-assets/numeric_observer.py'
    code=code_path.read_text(encoding='utf-8')
    code=pin_line(code,'PINNED_LEGACY_MASTER_SHA256',r"'[a-f0-9]{64}'",repr(base_master_sha))
    names=tuple(p['name_en'] for p in old['pokemon'])
    code=pin_line(code,'LEGACY_BASE_NAMES',r'\(.*\)',repr(names))
    code=pin_line(code,'LEGACY_BASE_SPECIES_SHA256',r"'[a-f0-9]{64}'",repr(canonical(old['pokemon'])))
    code,n=re.subn(r'len\(master\.get\(\x27pokemon\x27, \[\]\)\) != 249',"len(master.get('pokemon', [])) != 247",code)
    need(n==1,'BASE_COUNT_CHECK_UNEXPECTED')
    code,n=re.subn(r'not 249 < len\(species\)',r'not 247 < len(species)',code)
    need(n==1,'ADDITIONS_COUNT_CHECK_UNEXPECTED')
    code_path.write_text(code,encoding='utf-8')
    v['rawAssetSha256']['MASTER_DATA.json']=base_master_sha
    v['assetSha256']['MASTER_DATA.json']=canonical(old)
    v['rawAssetSha256']['numeric_observer.py']=sha(code_path.read_bytes())
    v['siteHotfixId']='SIMULATED_247_FOONGUS_AMOONGUSS_NO_RELEASE'
    need(v['productionCsvAllowed'] is False and v['compatibilityVerified'] is False and v['masterVerifiedAgainstLive'] is False,'HOLD_FLAG')
    ver_path.write_bytes(raw_json(v))
    # Before simulated promotion, the browser must agree with the simulated kit.
    app_path=dst/'app.js';a=app_path.read_text(encoding='utf-8')
    for key,val in [('SITE_HOTFIX_ID',v['siteHotfixId']),('KIT_VERSION_RAW_SHA256',sha(ver_path.read_bytes()))]:
        a,n=re.subn(r"(?m)^(const "+key+r" = ')[^']+(';)$",lambda m:m.group(1)+val+m.group(2),a)
        need(n==1,'NO_BROWSER_PIN:'+key)
    app_path.write_text(a,encoding='utf-8')
    need(independent_kit_verify(dst/'kit-assets')==247,'247_BASELINE_CONSUMER_REJECTED')
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_bytes(raw_json({'simulation':'TEST_ONLY_247_FROM_ACTUAL_249','baselineSpecies':247,
      'targets':list(ADDED),'baselineSha256':base_master_sha,'referenceSha256':sha((src/'kit-assets/MASTER_DATA.json').read_bytes()),
      'pinnedTestObserverSha256':sha(code_path.read_bytes()),'productionCsvAllowed':False}))
    print('SIMULATED_BASELINE_OK 247 targets absent; hardcoded test lineage; HOLD preserved')

def assert_candidate(source,site,stage,report):
    source,site,stage=Path(source),Path(site),Path(stage)
    ref=read(source/'kit-assets/MASTER_DATA.json');base=read(site/'kit-assets/MASTER_DATA.json')
    obj=read(stage/'MASTER_DATA.candidate.json');d=read(stage/'UPSTREAM_DIFF.json')
    need(len(base['pokemon'])==247 and len(obj['pokemon'])==249,'247_TO_249_COUNT_FAILURE')
    need(sorted(d['addedSpecies'])==sorted(ADDED),'DIFF_ADDED_NOT_EXACT_TWO: '+str(d['addedSpecies']))
    for key in ('removedSpecies','changedSpecies','newIngredientKeys','removedIngredientKeys','changedIngredientTranslations','newSubskillKeys','removedSubskillKeys','changedSubskillTranslations','newNatureKeys','removedNatureKeys','changedNatureTranslations'):
        need(not d[key],'UNEXPECTED_DELTA:'+key+' '+str(d[key]))
    ref_by={p['name_en']:p for p in ref['pokemon']}
    new_by={p['name_en']:p for p in obj['pokemon']}
    need(set(new_by)==set(ref_by),'CANDIDATE_SPECIES_SET_MISMATCH')
    for n in ref_by:need(new_by[n]==ref_by[n],'MASTER_VALUE_MISMATCH: '+n)
    for n in ('ingredients','natures','subskills'):
        need(obj[n]==ref[n],'MASTER_METADATA_MISMATCH: '+n)
    for en,ja in JA.items():need(new_by[en]['name']==ja,'WRONG_JAPANESE_NAME: '+en)
    need(d['sourceCommit']==obj['provenance']['sourceCommit'],'SOURCE_COMMIT_MISMATCH')
    out={'scenario':'TAMAGETAKE_MOROBARERU_SIMULATED_NEW_RELEASE','baseCount':247,'candidateCount':249,
         'addedSpecies':sorted(d['addedSpecies']),'sourceCommit':d['sourceCommit'],
         'twoSpecies':{n:new_by[n] for n in ADDED},'all249RecordsMatchReference':True,
         'old247RecordsUnchanged':True,'oldTranslationsUnchanged':True,'productionCsvAllowed':False}
    report.parent.mkdir(parents=True,exist_ok=True);report.write_bytes(raw_json(out))
    print('CANDIDATE_OK 247->249; all 249 data records exactly match original published 249; zero collateral changes')

def assert_vectors(csv_path,coverage_path,report):
    cov=read(coverage_path)
    with Path(csv_path).open(encoding='utf-8',newline='') as h:rows=list(csv.reader(h))
    need(cov['rows']==len(rows)-1 and len(rows)>=4,'NOT_ENOUGH_VECTORS')
    need(all(len(r)==16 for r in rows),'CSV_NOT_16_COLUMNS')
    need(sorted(cov['coveredNewSpecies'])==sorted(ADDED),'COVERAGE_TARGET_MISMATCH')
    for ja in JA.values():need(any(ja in row for row in rows[1:]),'MISSING_CSV_SPECIES:'+ja)
    v={'rows':len(rows)-1,'columns':16,'targets':list(JA.values()),'coverage':cov,'productionCsvAllowed':False}
    report.parent.mkdir(parents=True,exist_ok=True);report.write_bytes(raw_json(v))
    print('CSV_VECTORS_OK: contains Foongus, Amoonguss, plus historical control; 16 columns')

def assert_promoted(reference,sim,report):
    ref=read(Path(reference)/'kit-assets/MASTER_DATA.json')
    kit=Path(sim)/'kit-assets';master=read(kit/'MASTER_DATA.json');v=read(kit/'KIT_VERSION.json')
    need(independent_kit_verify(kit)==249,'PROMOTED_SPECIES_AUDIT_NOT_PASS')
    a={p['name_en']:p for p in master['pokemon']};b={p['name_en']:p for p in ref['pokemon']}
    need(a==b and len(a)==249,'PUBLISHED_GAMEPLAY_DATA_NOT_EXACT_REFERENCE')
    need(master['ingredients']==ref['ingredients'] and master['natures']==ref['natures'] and master['subskills']==ref['subskills'],'OTHER_MASTER_METADATA_CHANGED')
    need(v['productionCsvAllowed'] is False and v['compatibilityVerified'] is False and v['masterVerifiedAgainstLive'] is False,'PRODUCTION_GATE_CHANGED')
    for name,expected in v['rawAssetSha256'].items():
        p=kit/name
        need(p.is_file() and sha(p.read_bytes())==expected,'KIT_SHA_MISMATCH:'+name)
    need(sha((kit/'MASTER_DATA.json').read_bytes())==v['rawAssetSha256']['MASTER_DATA.json'],'MASTER_RAW_SHA_BAD')
    need('Foongus' in master['provenance'].get('verification','') or master['provenance']['verification'].startswith('PINNED_SOURCE'),'NO_SOURCE_ATTESTATION')
    out={'status':'SIMULATED_AUTOPROMOTION_TRANSACTION_PASS','promotedCount':249,'addedSpecies':list(ADDED),
         'all249RecordsMatchReference':True,'all16KitAssetsPinned':True,
         'masterSha256':sha((kit/'MASTER_DATA.json').read_bytes()),'versionSha256':sha((kit/'KIT_VERSION.json').read_bytes()),
         'productionCsvAllowed':False,'compatibilityVerified':False,'masterVerifiedAgainstLive':False}
    report.parent.mkdir(parents=True,exist_ok=True);report.write_bytes(raw_json(out))
    print('PROMOTED_SITE_OK: 249 species, all exact, 16-kit integrity, SpeciesAudit accepted, HOLD')

def tiny_png():
    data=bytes([0,123,45,67]);chunk=lambda n,b:struct.pack('>I',len(b))+n+b+struct.pack('>I',zlib.crc32(n+b)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(data))+chunk(b'IEND',b'')

def assert_ui_zip(site,report):
    from playwright.sync_api import sync_playwright
    site=Path(site).resolve()
    class Q(SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):super().__init__(*a,directory=str(site),**kw)
        def log_message(self,*args):pass
    httpd=ThreadingHTTPServer(('127.0.0.1',0),Q)
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            page=browser.new_page(accept_downloads=True)
            errors=[];page.on('pageerror',lambda exc: errors.append(str(exc)))
            page.goto(f'http://127.0.0.1:{httpd.server_port}/',wait_until='domcontentloaded',timeout=40000)
            # Real first-visit UX opens an onboarding TIPS modal. Close it as a user would.
            page.locator('#tipsDialog[open]').wait_for(state='visible',timeout=5000)
            page.locator('#tipsClose').click(timeout=5000)
            page.locator('#tipsDialog[open]').wait_for(state='hidden',timeout=5000)
            page.locator('#choose-files').set_input_files({'name':'test.png','mimeType':'image/png','buffer':tiny_png()})
            page.locator('#build').wait_for(state='visible',timeout=10000)
            page.wait_for_function("document.querySelector('#build') && !document.querySelector('#build').disabled",timeout=20000)
            with page.expect_download(timeout=75000) as info:page.locator('#build').click()
            target=info.value.path();payload=Path(target).read_bytes()
            with zipfile.ZipFile(io.BytesIO(payload)) as z:
                need(z.testzip() is None,'ZIP_BAD_CRC')
                names=z.namelist();need(len(names)==18,'ZIP_FILE_COUNT_NOT_18')
                for name in ('MASTER_DATA.json','KIT_VERSION.json','SPECIES_AUDIT.py','numeric_observer.py'):
                    need(z.read(name)==(site/'kit-assets'/name).read_bytes(),'ZIP_KIT_DIFF:'+name)
                master=json.loads(z.read('MASTER_DATA.json'))
                v=json.loads(z.read('KIT_VERSION.json'))
                need(len(master['pokemon'])==249 and all(any(x['name_en']==s for x in master['pokemon']) for s in ADDED),'ZIP_NOT_UPDATED_249')
                need(v['productionCsvAllowed'] is False,'ZIP_NOT_HOLD')
                manifest=json.loads(z.read('INPUT_MANIFEST.json'))
                entries=manifest['images']
                need(len(entries)==1,'IMAGE_MANIFEST_COUNT_BAD')
                image_entry=entries[0]
                need(image_entry['path'] in names,'IMAGE_MANIFEST_PATH_MISSING')
                need(z.read(image_entry['path'])==tiny_png(),'IMAGE_BYTES_BAD')
                need(image_entry['sha256']==sha(tiny_png()),'IMAGE_SHA256_BAD')
            need(not errors,'BROWSER_JS_ERRORS:'+str(errors))
            browser.close()
    finally:
        httpd.shutdown();thread.join(timeout=10)
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_bytes(raw_json({'status':'ACTUAL_BROWSER_ZIP_PASS','zipBytes':len(payload),'zipFiles':len(names),
        'newSpecies':list(ADDED),'actualBrowser':True,'uiOriginalImageBytesMatch':True,'all16KitFilesFromPromotedSite':True,
        'productionCsvAllowed':False}))
    print('BROWSER_ZIP_OK: actual Chrome at localhost; updated 249 master and original image bytes match')

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('prepare');a.add_argument('--src',required=True);a.add_argument('--dst',required=True);a.add_argument('--report',required=True)
    a=sub.add_parser('candidate');a.add_argument('--source',required=True);a.add_argument('--site',required=True);a.add_argument('--stage',required=True);a.add_argument('--report',required=True)
    a=sub.add_parser('vectors');a.add_argument('--csv',required=True);a.add_argument('--coverage',required=True);a.add_argument('--report',required=True)
    a=sub.add_parser('promoted');a.add_argument('--reference',required=True);a.add_argument('--site',required=True);a.add_argument('--report',required=True)
    a=sub.add_parser('ui-zip');a.add_argument('--site',required=True);a.add_argument('--report',required=True)
    q=p.parse_args()
    if q.cmd=='prepare':prepare(q.src,q.dst,Path(q.report))
    if q.cmd=='candidate':assert_candidate(q.source,q.site,q.stage,Path(q.report))
    if q.cmd=='vectors':assert_vectors(q.csv,q.coverage,Path(q.report))
    if q.cmd=='promoted':assert_promoted(q.reference,q.site,Path(q.report))
    if q.cmd=='ui-zip':assert_ui_zip(q.site,Path(q.report))
if __name__=='__main__':main()
