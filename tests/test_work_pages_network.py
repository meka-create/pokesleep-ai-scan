"""Offline fault injection: never invokes remote rollback."""
import os,sys,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError,URLError
sys.path.insert(0,str(Path(os.environ.get('AUDIT_SITE',str(Path(__file__).resolve().parents[1])))/'scripts'))
import verify_pages_live as p
class AssetNetwork(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.site=Path(self.tmp.name)
  for name in p.CHECK:
   path=self.site/name;path.parent.mkdir(parents=True,exist_ok=True)
   source=Path(__file__).resolve().parents[1]/'kit-assets/KIT_VERSION.json'
   path.write_bytes(source.read_bytes() if name=='kit-assets/KIT_VERSION.json' else name.encode())
 def getter(self,failure,wrong=False):
  def get(url):
   name=url.split('example.invalid/')[1].split('?')[0]
   if name=='app.js':raise failure
   if wrong and name=='kit-assets/MASTER_DATA.json':return b'wrong'
   return (self.site/name).read_bytes()
  return get
 def test_asset_timeout_is_unknown(self):
  with patch.object(p,'get',side_effect=self.getter(TimeoutError('timeout'))):
   self.assertEqual(p.classify(self.site,'https://example.invalid/','x')[0],'NETWORK_UNKNOWN')
 def test_asset_503_is_unknown(self):
  with patch.object(p,'get',side_effect=self.getter(HTTPError('https://example.invalid',503,'unavailable',{},None))):
   self.assertEqual(p.classify(self.site,'https://example.invalid/','x')[0],'NETWORK_UNKNOWN')
 def test_asset_dns_is_unknown(self):
  with patch.object(p,'get',side_effect=self.getter(URLError('DNS failure'))):
   self.assertEqual(p.classify(self.site,'https://example.invalid/','x')[0],'NETWORK_UNKNOWN')
 def test_three_network_failures_do_not_authorize_rollback(self):
  args=['verify','--site',str(self.site),'--url','https://example.invalid/','--commit','a'*40,'--attempts','3','--delay','0','--out',str(self.site/'result.json')]
  with patch.object(p,'get',side_effect=self.getter(TimeoutError('timeout'))),patch.object(sys,'argv',args):
   self.assertEqual(p.main(),4)
  self.assertEqual(json.loads((self.site/'result.json').read_text())['result'],'NETWORK_UNKNOWN')
 def test_proven_mismatch_even_if_another_request_fails(self):
  with patch.object(p,'get',side_effect=self.getter(TimeoutError('timeout'),True)):
   state,detail=p.classify(self.site,'https://example.invalid/','x')
  self.assertEqual(state,'MIXED_ASSETS_CONFIRMED');self.assertIn('kit-assets/MASTER_DATA.json',detail)
if __name__=='__main__':unittest.main(verbosity=2)
