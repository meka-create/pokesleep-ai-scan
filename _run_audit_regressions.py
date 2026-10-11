import pathlib, subprocess, json, sys, re, datetime
ROOT=pathlib.Path(__file__).resolve().parent
names=['test_additive_master_policy.py','test_additive_publisher_path.py','test_monitor_display_only_subskills.py','test_auto_watch.py','test_upstream_sync.py','test_import_compat_gate.py','test_verified_auto_promotion.py','test_upstream_preflight.py','test_daily_health.py','test_release_health.py','test_work_pages_network.py']
res=[]
for name in names:
    cmd=[sys.executable,'-m','unittest','discover','-s','tests','-p',name,'-q']
    try:
        p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=100,check=False)
        m=re.search(r'Ran (\d+) tests?', p.stdout+p.stderr)
        res.append(dict(name=name,number=int(m.group(1)) if m else None,pass_=p.returncode==0,tail=(p.stdout+p.stderr)[-800:]))
    except subprocess.TimeoutExpired:
        res.append(dict(name=name,number=None,pass_=False,timeout=True))
qa_cmd=[sys.executable,'-m','unittest','discover','-s','qa_step1_tests','-p','test_*.py','-q']
try:
    p=subprocess.run(qa_cmd,cwd=ROOT,capture_output=True,text=True,timeout=120,check=False)
    m=re.search(r'Ran (\d+) tests?',p.stdout+p.stderr)
    res.append(dict(name='qa_step1_tests',number=int(m.group(1)) if m else None,pass_=p.returncode==0,tail=(p.stdout+p.stderr)[-1500:]))
except subprocess.TimeoutExpired:
    res.append(dict(name='qa_step1_tests',number=None,pass_=False,timeout=True))
js=[]
for n in ['app.js','zip-store.js','ui-extras.js','update-status.js','sw.js']:
    p=subprocess.run(['node','--check',n],cwd=ROOT,capture_output=True,text=True,timeout=30)
    js.append(dict(file=n,pass_=p.returncode==0,stderr=p.stderr[-300:]))
obj={'timestampUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'suites':res,'js':js,'sumInvocations':sum(x['number'] or 0 for x in res),'allAvailableSuitesPass':all(x['pass_'] for x in res) and all(x['pass_'] for x in js),'excluded':['tests/test_import_probe_clipboard_v08.py: local Chromium live-network run timed out; not counted','End-to-end public importer (GitHub Actions manual pending)']}
(ROOT/'AUTOPROMOTION_RECOVERY_TEST_RESULTS.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
for r in res:print(f'{r["name"]:43} {r["number"]!s:>4} {"PASS" if r["pass_"] else "FAIL"}',flush=True)
print('JS checks:',[(x['file'],x['pass_']) for x in js])
print('ALL:',obj['allAvailableSuitesPass'],'INVOCATIONS:',obj['sumInvocations'])
if not obj['allAvailableSuitesPass']:
    for x in res:
        if not x['pass_']: print(x)
    raise SystemExit(1)
