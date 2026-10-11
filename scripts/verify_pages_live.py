#!/usr/bin/env python3
"""Classify GitHub Pages propagation versus provably mixed new page assets.

Never label stale CDN HTML a broken deployment. Return 2 only when the NEW
index is actually served but its pinned kit/app assets have proven byte mismatches.
Fetch failures alone are NETWORK_UNKNOWN and never authorize rollback.
"""
import argparse, hashlib, json, time, urllib.request
from pathlib import Path

# Include all files consumed by the ZIP/SpeciesAudit, not only its master.
# A partially deployed validator, instructions or master must never appear as
# a verified release. Paths are pinned to the trusted build's KIT_VERSION.
SHELL_CHECK=('index.html','app.js','sw.js','zip-store.js','ui-extras.js','styles.css',
             'kit-assets/KIT_VERSION.json')
CHECK=SHELL_CHECK+tuple('kit-assets/'+name for name in ('AI_INSTRUCTIONS.md','CSV_SCHEMA.json','MASTER_DATA.json',
    'PROGRESS_PROTOCOL.md','PROTOTYPE_EXPORT_GATE.py','READING_RULES.md','RECORDS_TEMPLATE.json',
    'RELEASE_EXPORT_GATE.py','SPECIES_AUDIT.py','SPECIES_AUDIT_GUIDE.md',
    'SPECIES_OBSERVATIONS_TEMPLATE.json','START_HERE.md','VALIDATOR.py','numeric_observer.py',
    'species_evidence_lab.py'))
def sha(b):return hashlib.sha256(b).hexdigest()
def get(url):
    req=urllib.request.Request(url,headers={'Cache-Control':'no-cache','Pragma':'no-cache','User-Agent':'PokeSleep-AutoWatch-Probe/1.0'})
    with urllib.request.urlopen(req,timeout=15) as f:
        if f.status!=200:raise OSError('HTTP '+str(f.status))
        return f.read()
def classify(site,url,token):
    site=Path(site);base=url.rstrip('/')+'/'
    try:index=get(base+'index.html?audit='+token)
    except Exception as e:return 'NETWORK_UNKNOWN', {'error':str(e)}
    expected_index=(site/'index.html').read_bytes()
    if index!=expected_index:
        return 'STALE_HTML_OR_PENDING_DEPLOYMENT', {'servedIndexSha256':sha(index),'expectedIndexSha256':sha(expected_index)}
    # No self-verified set expansion: the expected asset list is pinned by
    # publisher code; reject missing or altered KIT_VERSION inventory.
    try:
        inventory=json.loads((site/'kit-assets/KIT_VERSION.json').read_text(encoding='utf-8'))
        actual=set(inventory['rawAssetSha256'])
        wanted={p.removeprefix('kit-assets/') for p in CHECK if p.startswith('kit-assets/') and p!='kit-assets/KIT_VERSION.json'}
        if actual!=wanted or inventory['productionCsvAllowed'] is not False or inventory['compatibilityVerified'] is not False or inventory['masterVerifiedAgainstLive'] is not False:
            return 'NETWORK_UNKNOWN', {'error':'Invalid local release-kit inventory / HOLD'}
    except (OSError,KeyError,ValueError,TypeError):
        return 'NETWORK_UNKNOWN', {'error':'Invalid or missing local KIT_VERSION'}
    differences={}
    unavailable={}
    for file in CHECK[1:]:
        try:bytes_=get(base+file+'?audit='+token)
        except Exception as e:
            # A timeout, DNS failure, or HTTP error does not prove that the
            # deployed bytes differ. Never authorize rollback on outages alone.
            unavailable[file]='HTTP_ERROR:'+str(e);continue
        expected=(site/file).read_bytes()
        if bytes_!=expected:differences[file]={'expectedSha256':sha(expected),'servedSha256':sha(bytes_)}
    if differences:
        if unavailable: differences['unavailableAssets']=unavailable
        return 'MIXED_ASSETS_CONFIRMED',differences
    if unavailable:
        return 'NETWORK_UNKNOWN',{'unavailableAssets':unavailable}
    return 'ALL_EXPECTED_ASSETS_LIVE',{}

def main():
    p=argparse.ArgumentParser();p.add_argument('--site',required=True);p.add_argument('--url',required=True)
    p.add_argument('--commit',required=True);p.add_argument('--attempts',type=int,default=8);p.add_argument('--delay',type=int,default=40)
    p.add_argument('--out',required=True);a=p.parse_args()
    attempts=[]
    for n in range(max(1,a.attempts)):
        status,detail=classify(a.site,a.url,a.commit[:12]+f'-{n}')
        attempts.append({'result':status,'details':detail})
        if status=='ALL_EXPECTED_ASSETS_LIVE':break
        if n+1<a.attempts:time.sleep(a.delay)
    last=attempts[-1]['result']
    # CDN transitions can be briefly mixed; require three consecutive observations.
    if last=='MIXED_ASSETS_CONFIRMED' and (len(attempts)<3 or any(x['result']!='MIXED_ASSETS_CONFIRMED' for x in attempts[-3:])):
        last='MIXED_ASSETS_NOT_STABLE'
    result={'schema':'pokesleep-pages-health-v1','result':last,'checks':attempts,'productionCsvAllowed':False}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    print(last)
    # 2 is a hard mismatch ONLY after new HTML was served; 3 is stale/pending;
    # 4 is network unverified (do not roll back on mere temporary outages).
    return {'ALL_EXPECTED_ASSETS_LIVE':0,'MIXED_ASSETS_CONFIRMED':2,
            'STALE_HTML_OR_PENDING_DEPLOYMENT':3,'MIXED_ASSETS_NOT_STABLE':3,'NETWORK_UNKNOWN':4}[last]
if __name__=='__main__':raise SystemExit(main())
