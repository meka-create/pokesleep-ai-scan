"""Real HTTP/Chromium packaging regression for AI Scan prompt-only candidate.
Does not parse/guess Pokémon screenshots and validates a release-capable candidate only in isolated CI.
"""
import zipfile,hashlib,json,tempfile,time,threading,functools,http.server,os,re
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image
import random
ROOT=Path(__file__).resolve().parent
SITE=ROOT/'site' if (ROOT/'site').is_dir() else ROOT.parent if (ROOT.parent/'index.html').exists() else ROOT
sha=lambda x:hashlib.sha256(x).hexdigest()
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def main():
 with tempfile.TemporaryDirectory(prefix='ai_prompt_e2e_') as td:
  here=Path(td); source=here/'source';source.mkdir()
  baseline=[]
  # Distinct unedited PNGs, approximately 80MiB across 172 images.
  for i in range(172):
   rng=random.Random(i+20261011)
   im=Image.frombytes('RGB',(540,300),rng.randbytes(540*300*3))
   file=source/f'user-image-{i+1:03d}.png';im.save(file,'PNG',compress_level=0);baseline.append(file)
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(SITE)))
  t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
  report={'environment':'real-http Chromium, no injected crypto/fetch or navigator shim','sizes':[],'releaseCandidate':True}
  try:
   with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=['--no-sandbox'])
    for n in (10,30,100,172):
     context=b.new_context(accept_downloads=True)
     page=context.new_page()
     errors=[];page.on('pageerror',lambda exc:errors.append(str(exc)))
     page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='domcontentloaded',timeout=30000)
     prompt=page.locator('#prompt-text').inner_text()
     assert '全画像を実際に解析' in prompt and '他の画像の解析を進め' in prompt,prompt
     # Real first-visit UX: the TIPS modal intercepts pointer input until closed.
     page.locator('#tipsDialog[open]').wait_for(state='visible',timeout=10000)
     page.locator('#tipsClose').click()
     assert not page.locator('#tipsDialog').evaluate('(el) => el.open')
     start=time.monotonic()
     page.locator('#choose-files').set_input_files([str(x) for x in baseline[:n]])
     page.wait_for_function("() => !document.querySelector('#build').disabled",timeout=120000)
     with page.expect_download(timeout=120000) as d:page.locator('#build').click()
     dl=d.value;target=here/f'{n}.zip';dl.save_as(str(target))
     assert re.fullmatch(rf'AI_Bukkomi_Scan_{n}images_[0-9]{{8}}_[0-9]{{4}}(?:_[0-9]+)?[.]zip',dl.suggested_filename),dl.suggested_filename
     with zipfile.ZipFile(target) as z:
      assert z.testzip() is None
      names=z.namelist();assert len(names)==n+18,(n,len(names))
      assert len(set(names))==len(names)
      version=json.loads(z.read('KIT_VERSION.json'))
      assert version['productionCsvAllowed'] is True
      assert version['compatibilityVerified'] is True
      assert version['masterVerifiedAgainstLive'] is True
      assert len(version['rawAssetSha256'])==16
      for name,expected in version['rawAssetSha256'].items():assert sha(z.read(name))==expected,name
      man=json.loads(z.read('INPUT_MANIFEST.json'));assert len(man['images'])==n
      for i,x in enumerate(man['images']):
       raw=z.read(x['path']);assert raw==baseline[i].read_bytes(),(i,'bytes')
       assert sha(raw)==x['sha256'],(i,'sha')
      assert '一律な二度読み' in z.read('START_HERE.md').decode()
      reading=z.read('READING_RULES.md').decode('utf-8')
      assert z.read('RELEASE_EVIDENCE.json')
      assert '右端の食材3は' in reading and '枠色・隣枠の内容だけでランクや効果を決めない' in reading
      assert 'なお複数候補が残れば推測で確定せずユーザーに確認する' in reading
     if n==10:
      # Same-minute repeated creation must never reuse a filename.
      with page.expect_download(timeout=120000) as another:
       page.locator('#build').click()
      dl2=another.value
      assert dl2.suggested_filename!=dl.suggested_filename,(dl.suggested_filename,dl2.suggested_filename)
      assert re.fullmatch(r'AI_Bukkomi_Scan_10images_[0-9]{8}_[0-9]{4}(?:_[0-9]+)?[.]zip',dl2.suggested_filename)
      if dl2.suggested_filename[:-6]==dl.suggested_filename[:-4]:
       assert dl2.suggested_filename==dl.suggested_filename[:-4]+'_2.zip'
      target2=here/'10_repeat.zip'
      dl2.save_as(str(target2))
      with zipfile.ZipFile(target2) as z2:
       assert z2.testzip() is None
       assert len(z2.namelist())==28
     if n==10:
      # Saving the exact same ZIP must also allocate a fresh name.
      with page.expect_download(timeout=30000) as repeated_save:
       page.locator('#redownload').click()
      saved_again=repeated_save.value
      assert saved_again.suggested_filename not in (dl.suggested_filename,dl2.suggested_filename)
      assert re.fullmatch(r'AI_Bukkomi_Scan_10images_[0-9]{8}_[0-9]{4}(?:_[0-9]+)?[.]zip',saved_again.suggested_filename)
      target3=here/'10_redownload.zip'
      saved_again.save_as(str(target3))
      assert target3.read_bytes()==target2.read_bytes()
     assert not errors,errors
     result={'n':n,'zipBytes':target.stat().st_size,'elapsedSeconds':round(time.monotonic()-start,2),'entries':n+18,'downloadFilename':dl.suggested_filename,'originalImageSha256Match':True,'kitShaMatch':True,'jsErrors':0}
     report['sizes'].append(result);print('PASS',result,flush=True);context.close()
    b.close()
  finally:
   server.shutdown();t.join(timeout=5)
  (ROOT/'RELEASE_BROWSER_RESULTS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  print('RESULT',json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
