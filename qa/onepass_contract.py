"""Independent static contract for first-pass reading instructions (NO Golden data)."""
import hashlib
import json
import re
from pathlib import Path
R=Path(__file__).resolve().parents[1]
K=R/'kit-assets'
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((K/'KIT_VERSION.json').read_text())
assert (v['productionCsvAllowed'],v['compatibilityVerified'],v['masterVerifiedAgainstLive']) == (False,False,False)
assert len(v['rawAssetSha256'])==15
assert set(v['rawAssetSha256']) == {p.name for p in K.iterdir() if p.is_file()} - {'KIT_VERSION.json'}
for file,expected in v['rawAssetSha256'].items(): assert H(K/file)==expected,file
for file in ('MASTER_DATA.json','CSV_SCHEMA.json'):
 canon=hashlib.sha256(json.dumps(json.loads((K/file).read_text()),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 assert v['assetSha256'][file]==canon,file
assert H(K/'MASTER_DATA.json')=='d60410ba1f92d80c67ca3ff40bc8aa7a2cd51d4c03fc33f9e99fa83bb8e77a38'
s=(R/'app.js').read_text()
assert f"KIT_VERSION_RAW_SHA256 = '{H(K/'KIT_VERSION.json')}'" in s
assert f"SITE_HOTFIX_ID = '{v['siteHotfixId']}'" in s
assert v['siteHotfixId'] in (R/'sw.js').read_text()
assert './app.js?v=v19-faded-subskill-onepass-20261011' in (R/'index.html').read_text()
assert 'update-watch-close-bottom' not in (R/'index.html').read_text()
for f in ('AI_INSTRUCTIONS.md','READING_RULES.md','SPECIES_AUDIT_GUIDE.md'):
 s=(K/f).read_text()
 for mark in ('ニックネーム','メインスキル','サブスキル','全画像','初回'):
  assert mark in s,(f,mark)
 if f!='SPECIES_AUDIT_GUIDE.md': assert 'Lv10' in s and 'Lv80' in s,(f,'lv')
 for id in ('IMG-0127','IMG-0131','IMG-0140','IMG-0164','IMG-0166'):
  assert id not in s,(f,'blind reference contamination')
assert '未解放' in (K/'AI_INSTRUCTIONS.md').read_text()
assert '解放済みではレベル札が非表示' in (K/'READING_RULES.md').read_text()
assert '文字が薄い未解放枠でも' in (K/'READING_RULES.md').read_text()
assert 'その枠だけ元画像を画素非改変で拡大・再確認' in (K/'READING_RULES.md').read_text()
assert '全画像の一律な二度読み' in (K/'START_HERE.md').read_text()
assert (K/'PROGRESS_PROTOCOL.md').read_text().startswith('# 画像解析・報告の確定運用')
assert not ('Golden172' in (R/'app.js').read_text())
print('PASS: 15 raw SHA + 2 canonical + frozen 249 master + 3 HOLD + hotfix pins + one-pass evidence rules, no Golden labels')
