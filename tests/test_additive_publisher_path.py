"""Full synthetic privileged transaction test; not actual browser E2E proof."""
from __future__ import annotations
import copy,json,shutil,hashlib,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'kit-assets'))
from test_verified_auto_promotion import AutoPromotionTests, SHA, BASE, RUN, save
from verified_auto_promotion import build_patch, digest, canonical_digest
from publish_auto_result import require_staged_species_audit_compatible,execute
from build_auto_vectors import build as build_vectors
from sync_upstream import project
from SPECIES_AUDIT import verify_bundle

class TestAdditivePromotionTransaction(unittest.TestCase):
 def setUp(self):
  AutoPromotionTests.setUp(self)
  # Restore actual v18 baseline (not the legacy 247-fixture test baseline).
  src=ROOT/'kit-assets'
  shutil.copy2(src/'MASTER_DATA.json',self.site/'kit-assets/MASTER_DATA.json')
  shutil.copy2(src/'KIT_VERSION.json',self.site/'kit-assets/KIT_VERSION.json')
  self.old=json.loads((src/'MASTER_DATA.json').read_text())
  new=copy.deepcopy(self.source.src_json[0]);new.update(id=100000,name='SyntheticApprovedAddedSpecies',arrival='2026-10-10')
  self.source.src_json.append(new)
  self.source.names['SyntheticApprovedAddedSpecies']='テスト追加種（自動昇格模擬）'
  self.source.write()
  for rel in ('src/data/pokemon.json','src/i18n/ja/pokemons.json','src/i18n/ja/data.json',
              'src/i18n/ja/skills.json','src/util/SubSkill.ts'):
   shutil.copy2(self.source.base/rel,self.bundle/'upstream_source'/rel)
  candidate,diff=project(self.source.base,self.old,allow_fixture=True)
  candidate['provenance']['sourceCommit']=SHA
  diff['sourceCommit']=SHA
  assert diff['addedSpecies']==['SyntheticApprovedAddedSpecies'],diff
  assert not diff['changedSpecies'],diff
  save(self.bundle/'MASTER_DATA.candidate.json',candidate)
  save(self.bundle/'UPSTREAM_DIFF.json',diff)
  coverage=build_vectors(self.bundle/'MASTER_DATA.candidate.json',self.bundle/'UPSTREAM_DIFF.json',
      self.bundle/'AUTO_VECTORS.csv',self.bundle/'VECTOR_COVERAGE.json')
  shutil.copy2(self.bundle/'AUTO_VECTORS.csv',self.bundle/'roundtrip_export.csv')
  shutil.copy2(self.bundle/'AUTO_VECTORS.csv',self.bundle/'live_roundtrip_export.csv')
  for name in ('PROBE_RESULT.json','LIVE_PROBE_RESULT.json'):
   data=json.loads((self.bundle/name).read_text())
   data['inputCsvRowCount']=coverage['rows']
   save(self.bundle/name,data)
  proof=json.loads((self.bundle/'PROMOTION_PROOF.json').read_text())
  for p_name,f in {'candidateSha256':'MASTER_DATA.candidate.json',
     'diffSha256':'UPSTREAM_DIFF.json','vectorCsvSha256':'AUTO_VECTORS.csv',
     'coverageSha256':'VECTOR_COVERAGE.json','browserProbeSha256':'PROBE_RESULT.json',
     'browserExportSha256':'roundtrip_export.csv','liveBrowserProbeSha256':'LIVE_PROBE_RESULT.json',
     'liveBrowserExportSha256':'live_roundtrip_export.csv'}.items():
   proof[p_name]=digest(self.bundle/f)
  proof['verifiedTestVectors']=coverage['rows']
  save(self.bundle/'PROMOTION_PROOF.json',proof)

 def test_synthetic_additive_patch_consumer_and_atomic_publish(self):
  out=self.root/'patch'
  receipt=build_patch(self.bundle,self.site,out,run_id=RUN,base_sha=BASE)
  self.assertEqual(receipt['addedSpecies'],['SyntheticApprovedAddedSpecies'])
  names=['kit-assets/MASTER_DATA.json','kit-assets/KIT_VERSION.json','kit-assets/numeric_observer.py']
  patchdata={name:(out/name).read_bytes() for name in names}
  require_staged_species_audit_compatible(self.site,patchdata)
  with patch('publish_auto_result.build_patch',side_effect=lambda bundle,site,out,**k: build_patch(bundle,site,out,run_id=RUN,base_sha=BASE)):
   status=self.root/'status.json'
   save(status, {'schemaVersion':'pokesleep-upstream-status-v1','state':'healthy',
       'checkedAt':'2026-10-10T00:00:00Z','upstreamCommit':SHA,'activeSourceCommit':None,
       'reasonCode':'UPSTREAM_VERIFIED','message':'ok','details':'ok','productionCsvAllowed':False})
   result=execute(self.site,self.bundle,self.source.base,audit_status=status,audit_result='success',run_id=RUN,base_sha=BASE)
  self.assertTrue(result['promoted'])
  # Import the staged kit's own pinned numeric module in an isolated process.
  import subprocess
  cli='import sys,pathlib,json;sys.path.insert(0,sys.argv[1]);from SPECIES_AUDIT import verify_bundle;m,v=verify_bundle(pathlib.Path(sys.argv[1]));print(len(m["pokemon"]))'
  proc=subprocess.run([sys.executable,'-c',cli,str(self.site/'kit-assets')],capture_output=True,text=True,timeout=10,check=True)
  self.assertEqual(proc.stdout.strip(),'250')
  v=json.loads((self.site/'kit-assets/KIT_VERSION.json').read_text())
  self.assertFalse(v['productionCsvAllowed'])
  self.assertFalse(v['compatibilityVerified'])
  self.assertFalse(v['masterVerifiedAgainstLive'])
  self.assertEqual(v['sourceCommit'],SHA)
  self.assertEqual(digest(self.site/'kit-assets/MASTER_DATA.json'),v['rawAssetSha256']['MASTER_DATA.json'])
  self.assertEqual(result['changedPaths'],['app.js','index.html','sw.js','kit-assets/MASTER_DATA.json','kit-assets/KIT_VERSION.json','kit-assets/numeric_observer.py','update-status.json'])

if __name__=='__main__':unittest.main()
