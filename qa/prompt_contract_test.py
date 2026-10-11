"""Static independent prompt/ZIP contract regression; no trusted reference answers."""
from pathlib import Path
import json,hashlib,re,sys,html,zipfile
HERE=Path(__file__).resolve().parent
R=HERE/'site' if (HERE/'site').is_dir() else HERE.parent if (HERE.parent/'index.html').exists() else HERE
K=R/'kit-assets'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((K/'KIT_VERSION.json').read_text())
assert v['productionCsvAllowed'] is False and v['compatibilityVerified'] is False and v['masterVerifiedAgainstLive'] is False
assert v['kitVersion']=='0.12.0-prototype'
assert len(v['rawAssetSha256'])==15
assert set(v['rawAssetSha256'])=={p.name for p in K.iterdir() if p.is_file()}-{'KIT_VERSION.json'}
for name,value in v['rawAssetSha256'].items():assert sha(K/name)==value,name
for name in ('MASTER_DATA.json','CSV_SCHEMA.json'):
 payload=json.loads((K/name).read_text())
 canonical=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 assert v['assetSha256'][name]==canonical,name
j=(R/'app.js').read_text();m=re.search(r"KIT_VERSION_RAW_SHA256 = '([a-f0-9]{64})'",j)
assert m and m.group(1)==sha(K/'KIT_VERSION.json')
assert f"SITE_HOTFIX_ID = '{v['siteHotfixId']}'" in j
assert v['siteHotfixId'] in (R/'sw.js').read_text()
assert 'app.js?v=v18-prompt-ops-review-20261011' in (R/'index.html').read_text()
prompt=html.unescape(re.search(r'<p class="prompt-text" id="prompt-text">(.+?)</p>',(R/'index.html').read_text()).group(1))
for phrase in ['START_HERE.md','INPUT_MANIFEST.json','全画像を実際に解析','他の画像の解析を進め','統合検証','未検証のCSVは出力しない']:
 assert phrase in prompt,phrase
for name in ('START_HERE.md','AI_INSTRUCTIONS.md','READING_RULES.md','SPECIES_AUDIT_GUIDE.md','PROGRESS_PROTOCOL.md'):
 s=(K/name).read_text()
 assert '本番' in s and 'HOLD' in s,name
 assert '未確認' in s or '不確定' in s or '確認' in s,name
 assert '2巡' not in s or '二巡' in s or '一律' in s
assert '全画像の一律な二度読みを要求しない' in (K/'START_HERE.md').read_text()
assert '保留画像の確定とCSV出力はユーザーの実回答まで停止' in (K/'AI_INSTRUCTIONS.md').read_text()
assert '一緒に眠った時間' in (K/'READING_RULES.md').read_text()
assert 'formSizeMinimumCarryCertificate' in (K/'SPECIES_AUDIT_GUIDE.md').read_text()
assert '確定J' in (K/'PROGRESS_PROTOCOL.md').read_text()
assert 'Golden172などの正解ラベルは画像解析用ZIPには同梱しない' in (K/'PROGRESS_PROTOCOL.md').read_text()
print('PASS: 15 raw kit SHA, 2 canonical SHA, 3 HOLD flags, app anchor, SW cache, UI prompt, document gates')
