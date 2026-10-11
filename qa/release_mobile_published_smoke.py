#!/usr/bin/env python3
"""Live GitHub Pages mobile Chromium workflow smoke; browser-only synthetic image.

Never sends the selected image to third parties; confirms ZIP + manifest + raw
image bytes match, and that released CSV flags are true and trusted kit files are complete.
"""
import hashlib
import io
import json
import pathlib
import zipfile
import re
from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE=ROOT/'icons/icon-192.png'
OUT=ROOT/'release_mobile_evidence'
OUT.mkdir(exist_ok=True)
EXPECTED=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
URL='https://meka-create.github.io/pokesleep-ai-scan/'
result={'mode':'PUBLISHED_MOBILE_CHROMIUM_READONLY','url':URL,'mobileViewport':'390x844',
        'productionCsvAllowed':True,'selectedImageBytesUnchanged':False,'manifestSHA':False,
        'zipCRC':False,'downloadObserved':False,'consoleErrors':[]}
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(viewport={'width':390,'height':844},
        device_scale_factor=2,is_mobile=True,has_touch=True,accept_downloads=True,locale='ja-JP')
    page=context.new_page()
    page.on('pageerror',lambda error:result['consoleErrors'].append(str(error)))
    try:
        expected_kit=json.loads((ROOT/'release-kit-assets/KIT_VERSION.json').read_text(encoding='utf-8'))
        # On GitHub Pages, push-triggered tests can start before the new
        # deployment has propagated. Do not mistake the preceding release for
        # a broken app. Retry the actual public HTML and kit together.
        for attempt in range(12):
            r=page.goto(URL+'?release_audit='+str(attempt),
                        wait_until='domcontentloaded',timeout=45000)
            html=page.content()
            response=page.request.get(
                URL+'release-kit-assets/KIT_VERSION.json?release_audit='+str(attempt),
                timeout=20000,headers={'Cache-Control':'no-cache'})
            try:
                live_kit=response.json() if response.ok else {}
            except Exception:
                live_kit={}
            if (r and r.status==200 and
                live_kit.get('siteHotfixId')==expected_kit['siteHotfixId'] and
                'app.js?v='+expected_kit['siteHotfixId'] in html):
                result['siteReadyAttempt']=attempt+1
                break
            if attempt==11:
                raise AssertionError('PUBLIC_RELEASE_PROPAGATION_UNVERIFIED: '+str(live_kit.get('siteHotfixId')))
            page.wait_for_timeout(15000)
        page.locator('#choose-files').wait_for(state='attached',timeout=15000)
        page.screenshot(path=str(OUT/'01_public_mobile.png'),full_page=True)
        modal=page.locator('#tipsDialog')
        if modal.count() and modal.is_visible():
            close=page.locator('#tipsClose')
            if close.count() and close.is_visible():
                close.click()
        page.locator('#choose-files').set_input_files(str(SOURCE))
        page.screenshot(path=str(OUT/'02_after_selected.png'),full_page=True)
        page.wait_for_function("() => document.querySelector('#build') && !document.querySelector('#build').disabled",timeout=25000)
        page.screenshot(path=str(OUT/'02_mobile_selected.png'),full_page=True)
        with page.expect_download(timeout=90000) as info:
            page.locator('#build').click()
        download=info.value
        result['suggestedFilename']=download.suggested_filename
        assert re.fullmatch(r'AI_Bukkomi_Scan_1images_[0-9]{8}_[0-9]{4}(?:_[0-9]+)?[.]zip',download.suggested_filename)
        path=OUT/'mobile_download.zip'
        download.save_as(str(path))
        result['downloadObserved']=True
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            result['zipCRC']=True
            manifest=json.loads(z.read('INPUT_MANIFEST.json'))
            assert manifest['inputImageCount']==1
            image=manifest['images'][0]
            fileBytes=z.read(image['path'])
            assert fileBytes==SOURCE.read_bytes()
            assert image['sha256']==EXPECTED
            result['selectedImageBytesUnchanged']=True
            result['manifestSHA']=True
            kit=json.loads(z.read('KIT_VERSION.json'))
            assert kit['productionCsvAllowed'] is True
            assert kit['compatibilityVerified'] is True
            assert kit['masterVerifiedAgainstLive'] is True
            result['kitHotfixId']=kit['siteHotfixId']
            result['kitFiles']=len(z.namelist())-2
            assert result['kitFiles']==17
            assert 'RELEASE_EVIDENCE.json' in z.namelist()
            # Verify the deployed ZIP against the CURRENT checked-out release
            # pin. A hard-coded older tag would break every future release.
            assert kit['siteHotfixId']==expected_kit['siteHotfixId']
        page.screenshot(path=str(OUT/'03_mobile_ready.png'),full_page=True)
    finally:
        browser.close()
(OUT/'MOBILE_SMOKE_RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert result['downloadObserved'] and result['manifestSHA'] and result['zipCRC']
assert not result['consoleErrors'],result['consoleErrors']
print(json.dumps(result,ensure_ascii=False,indent=2))
