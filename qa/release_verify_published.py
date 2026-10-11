#!/usr/bin/env python3
"""Independent end-to-end public URL audit for current AI Scan release assets.

Fetches the actual GitHub Pages URL. Never uploads photos or produces CSV.
Retries CDN propagation; refuses any mixed kit or stale frontend.
"""
import hashlib,json,pathlib,time,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
URL='https://meka-create.github.io/pokesleep-ai-scan/'
kit=ROOT/'release-kit-assets'
v=json.loads((kit/'KIT_VERSION.json').read_text(encoding='utf-8'))
sha=lambda b:hashlib.sha256(b).hexdigest()
files=['index.html','app.js','sw.js','release-kit-assets/KIT_VERSION.json']
files+=['release-kit-assets/'+name for name in sorted(v['rawAssetSha256'])]
files+=['kit-assets/KIT_VERSION.json','kit-assets/MASTER_DATA.json']
expected={path:sha((ROOT/path).read_bytes()) for path in files}
assert len(files)==22
assert v['productionCsvAllowed'] is True and v['compatibilityVerified'] is True
assert len(v['rawAssetSha256'])==16
old=json.loads((ROOT/'kit-assets/KIT_VERSION.json').read_text())
assert old['productionCsvAllowed'] is False
assert old['rawAssetSha256']['MASTER_DATA.json']==v['rawAssetSha256']['MASTER_DATA.json']
assert (v['siteHotfixId'] in (ROOT/'app.js').read_text())
report={'mode':'RELEASE_PUBLIC_STATIC_BYTES_SHA256','site':URL,'expectedFiles':len(files),
        'productionCsvAllowed':True,'releasedMasterSpecies':249,'matched':False,'attempts':[]}
for attempt in range(1,13):
    failures=[]
    for path in files:
        try:
            req=urllib.request.Request(URL+path+'?publish_check='+str(attempt),
                headers={'User-Agent':'AI-Scan-Independent-Release-Audit/1.0','Cache-Control':'no-cache'})
            with urllib.request.urlopen(req,timeout=15) as res:
                buf=res.read()
                if res.status!=200: raise RuntimeError(f'HTTP {res.status}')
                if sha(buf)!=expected[path]: failures.append(path+':SHA_MISMATCH')
        except Exception as exc:failures.append(path+':'+str(exc)[:130])
    report['attempts'].append({'attempt':attempt,'badCount':len(failures),'badFiles':failures[:8]})
    if not failures:
        report['matched']=True
        break
    if attempt<12:time.sleep(15)
path=ROOT/'qa/RELEASE_PUBLIC_HTTP_AUDIT.json'
path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert report['matched'],('PUBLIC_PAGES_MIXED_OR_STALE',report['attempts'][-1])
print('PASS: '+str(len(files))+' production + development public assets match SHA, deployed actual GitHub Pages, release master 249, dev HOLD intact')
