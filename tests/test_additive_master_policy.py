"""Independent offline policy tests: a fake proof never qualifies as live E2E."""
from __future__ import annotations
import unittest,tempfile,json,hashlib,copy,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'kit-assets'))
from numeric_observer import verify_additive_legacy_master,observed_numeric,LEGACY_BASE_NAMES
from SPECIES_AUDIT import verify_bundle,audit_record

def b(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
def h(x):return hashlib.sha256(x).hexdigest()

class TestAdditiveMasterPolicy(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.master=json.loads((ROOT/'kit-assets/MASTER_DATA.json').read_text('utf-8'))
  cls.version=json.loads((ROOT/'kit-assets/KIT_VERSION.json').read_text('utf-8'))

 def candidate(self):
  m=copy.deepcopy(self.master);v=copy.deepcopy(self.version)
  p=copy.deepcopy(m['pokemon'][0]);p['name']='独立監査対象テスト種';p['name_en']='SyntheticNewSpeciesNeverForRelease'
  m['pokemon'].append(p)
  m['provenance'].update(sourceCommit='1'*40,importerProofSha256='2'*64,
      verification='PINNED_SOURCE_AND_LIVE_PUBLIC_IMPORTER_CSV_ROUNDTRIP_PASS; PRODUCTION_CSV_HOLD')
  v['sourceCommit']='1'*40
  v['rawAssetSha256']['MASTER_DATA.json']=h(b(m))
  v['assetSha256']['MASTER_DATA.json']=h(json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
  return m,v

 def pinned(self,master):
  return patch('numeric_observer.TRUSTED_PROMOTED_MASTER_SHA256',h(b(master)))

 def test_exact_legacy_master(self):
  self.assertEqual(verify_additive_legacy_master(self.master,b(self.master),self.version)['policy'],'PINNED_V18_LEGACY')
  self.assertEqual(len(LEGACY_BASE_NAMES),249)

 def test_master_plus_self_claimed_metadata_is_not_approved(self):
  m,v=self.candidate()
  with self.assertRaisesRegex(ValueError,'not independently pinned'):
   verify_additive_legacy_master(m,b(m),v)
  # Even a matching raw/canonical KIT_VERSION digest cannot bypass the code pin.
  with tempfile.TemporaryDirectory() as td:
   import shutil
   k=Path(td)/'kit-assets';shutil.copytree(ROOT/'kit-assets',k)
   (k/'MASTER_DATA.json').write_bytes(b(m));(k/'KIT_VERSION.json').write_bytes(b(v))
   with self.assertRaisesRegex(ValueError,'not independently pinned'):
    verify_bundle(k)

 def test_publisher_pinned_addition_requires_visible_review(self):
  m,v=self.candidate()
  with self.pinned(m):
   self.assertEqual(verify_additive_legacy_master(m,b(m),v)['newSpecies'],('SyntheticNewSpeciesNeverForRelease',))
   r=audit_record(m,{'imageId':'test-1','decision':'include','data':{
      'species':'独立監査対象テスト種','foods':[None,None,None],
      'mainSkill':m['pokemon'][-1]['mainSkill'],'level':10,'nature':None,
      'subskills':[None]*5,'fieldEvidence':{}}},{})
   self.assertTrue(r['newMasterSpeciesReviewRecommended'])
   self.assertTrue(r['speciesIdentityReviewRecommended'])
   numeric=observed_numeric('独立監査対象テスト種',m,{'level':10,
      'nature':m['natures'][0]['ja'], 'subskills':[s['ja'] for s in m['subskills'][:5]],'sp':10})
   self.assertEqual(numeric['status'],'NEW_SPECIES_NUMERIC_HOLD')

 def test_mutated_historical_species_rejected_even_with_new_publisher_pin(self):
  m,v=self.candidate();m['pokemon'][0]['carryLimit']+=1
  v['rawAssetSha256']['MASTER_DATA.json']=h(b(m))
  with self.pinned(m),self.assertRaisesRegex(ValueError,'Historical species gameplay'):
   verify_additive_legacy_master(m,b(m),v)

 def test_modified_historical_translation_rejected(self):
  m,v=self.candidate();m['ingredients'][next(iter(m['ingredients']))]='危険な置換'
  with self.pinned(m),self.assertRaisesRegex(ValueError,'ingredient translations'):
   verify_additive_legacy_master(m,b(m),v)

 def test_new_subskill_semantics_rejected(self):
  m,v=self.candidate();m['subskills'].append({'en':'unapproved','ja':'未承認'})
  with self.pinned(m),self.assertRaisesRegex(ValueError,'new subskill'):
   verify_additive_legacy_master(m,b(m),v)

 def test_missing_independent_e2e_proof_rejected(self):
  m,v=self.candidate();m['provenance'].pop('importerProofSha256')
  with self.pinned(m),self.assertRaisesRegex(ValueError,'independently validated'):
   verify_additive_legacy_master(m,b(m),v)

 def test_only_249_without_baseline_raw_pin_is_held(self):
  m,v=self.candidate();m['pokemon'].pop()
  with self.pinned(m),self.assertRaisesRegex(ValueError,'species cardinality'):
   verify_additive_legacy_master(m,b(m),v)

 def test_hold_flags_cannot_be_lifted(self):
  m,v=self.candidate();v['productionCsvAllowed']=True
  with self.pinned(m),self.assertRaisesRegex(ValueError,'HOLD policy'):
   verify_additive_legacy_master(m,b(m),v)

if __name__=='__main__':unittest.main()
