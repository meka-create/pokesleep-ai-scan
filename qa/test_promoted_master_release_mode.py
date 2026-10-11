"""Promoted-master development HOLD and approved-release branches share legacy anchors.

A synthetic 250th species is for a test only, never an accepted master update.
"""
import copy
import hashlib
import json
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
KIT=ROOT/'kit-assets'
sys.path.insert(0,str(KIT))
import numeric_observer as numeric
import SPECIES_AUDIT as species

def canon(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def raw(obj):
    return (json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()

class PromotedMasterReleaseTests(unittest.TestCase):
    def fixture(self):
        master=json.loads((KIT/'MASTER_DATA.json').read_text(encoding='utf-8'))
        ext=copy.deepcopy(master['pokemon'][0])
        ext['name_en']='QA-Synthetic-250'
        ext['name']='監査専用の仮想追加種'
        master['pokemon'].append(ext)
        commit='a'*40
        master['provenance']={
          'sourceCommit':commit,
          'verification':numeric.AUTO_PROMOTION_VERIFICATION,
          'importerProofSha256':'b'*64
        }
        ver=json.loads((KIT/'KIT_VERSION.json').read_text(encoding='utf-8'))
        ver['sourceCommit']=commit
        ver['assetSha256']['MASTER_DATA.json']=canon(master)
        ver['rawAssetSha256']['MASTER_DATA.json']=hashlib.sha256(raw(master)).hexdigest()
        return master,ver

    def test_promoted_master_still_requires_development_hold(self):
        master,version=self.fixture()
        with patch.object(numeric,'TRUSTED_PROMOTED_MASTER_SHA256',hashlib.sha256(raw(master)).hexdigest()):
            report=numeric.verify_additive_legacy_master(master,raw(master),version)
            self.assertEqual(report['policy'],'ADDITIONS_ONLY_WITH_PINNED_LEGACY')
            self.assertEqual(report['newSpecies'],('QA-Synthetic-250',))
            with self.assertRaisesRegex(ValueError,'release eligibility'):
                numeric.verify_additive_legacy_master(master,raw(master),version,allow_release=True)

    def test_release_route_requires_all_three_explicit_flags(self):
        master,version=self.fixture()
        version['kitVersion']='0.12.1-release'
        version['status']='RELEASE_APPROVED'
        version.update(productionCsvAllowed=True,compatibilityVerified=True,masterVerifiedAgainstLive=True)
        with patch.object(numeric,'TRUSTED_PROMOTED_MASTER_SHA256',hashlib.sha256(raw(master)).hexdigest()):
            with self.assertRaisesRegex(ValueError,'HOLD policy'):
                numeric.verify_additive_legacy_master(master,raw(master),version)
            result=numeric.verify_additive_legacy_master(master,raw(master),version,allow_release=True)
            self.assertEqual(result['newSpecies'],('QA-Synthetic-250',))
            for flag in ('productionCsvAllowed','compatibilityVerified','masterVerifiedAgainstLive'):
                invalid=dict(version);invalid[flag]=False
                with self.assertRaisesRegex(ValueError,'release eligibility'):
                    numeric.verify_additive_legacy_master(master,raw(master),invalid,allow_release=True)
            invalid=dict(version);invalid['kitVersion']='0.12.0-prototype'
            with self.assertRaisesRegex(ValueError,'release eligibility'):
                numeric.verify_additive_legacy_master(master,raw(master),invalid,allow_release=True)

    def test_species_audit_promoted_release_wiring_and_pins(self):
        master,version=self.fixture()
        version['kitVersion']='0.12.1-release'
        version['status']='RELEASE_APPROVED'
        version.update(productionCsvAllowed=True,compatibilityVerified=True,masterVerifiedAgainstLive=True)
        with tempfile.TemporaryDirectory() as td:
            folder=pathlib.Path(td)
            (folder/'MASTER_DATA.json').write_bytes(raw(master))
            shutil.copy2(KIT/'CSV_SCHEMA.json',folder/'CSV_SCHEMA.json')
            shutil.copy2(KIT/'SPECIES_AUDIT.py',folder/'SPECIES_AUDIT.py')
            shutil.copy2(KIT/'numeric_observer.py',folder/'numeric_observer.py')
            (folder/'KIT_VERSION.json').write_bytes(raw(version))
            with patch.object(numeric,'TRUSTED_PROMOTED_MASTER_SHA256',hashlib.sha256(raw(master)).hexdigest()):
                verified,_=species.verify_bundle(folder,allow_release=True)
                self.assertEqual(len(verified['pokemon']),250)
                with self.assertRaisesRegex(ValueError,'HOLD/version'):
                    species.verify_bundle(folder,allow_release=False)

    def test_tampered_promoted_legacy_species_still_rejected(self):
        master,version=self.fixture()
        originalSHA=hashlib.sha256(raw(master)).hexdigest()
        with patch.object(numeric,'TRUSTED_PROMOTED_MASTER_SHA256',originalSHA):
            master['pokemon'][0]['frequency']+=1
            version['kitVersion']='0.12.1-release'
            version.update(productionCsvAllowed=True,compatibilityVerified=True,masterVerifiedAgainstLive=True)
            version['rawAssetSha256']['MASTER_DATA.json']=hashlib.sha256(raw(master)).hexdigest()
            with self.assertRaises(ValueError):
                numeric.verify_additive_legacy_master(master,raw(master),version,allow_release=True)

if __name__=='__main__': unittest.main()
