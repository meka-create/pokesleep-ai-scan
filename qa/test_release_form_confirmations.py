"""Independent regression: user-confirmed form sizes must reach dormant release gate.

No Golden labels, no production releases, no user-data files.
"""
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'kit-assets'))
import RELEASE_EXPORT_GATE as release

class ReleaseFormConfirmationsTests(unittest.TestCase):
    def test_current_production_still_hold(self):
        version = json.loads((ROOT / 'kit-assets/KIT_VERSION.json').read_text(encoding='utf-8'))
        self.assertIs(version['productionCsvAllowed'], False)
        self.assertIs(version['compatibilityVerified'], False)
        self.assertIs(version['masterVerifiedAgainstLive'], False)
        with self.assertRaisesRegex(ValueError, 'HOLD'):
            release.release_preflight(ROOT / 'kit-assets', None, False)
        with self.assertRaises(ValueError):
            release.release_preflight(ROOT / 'kit-assets', None, True)

    def test_release_cli_exposes_user_confirmations(self):
        done = subprocess.run([sys.executable, str(ROOT / 'kit-assets/RELEASE_EXPORT_GATE.py'), '--help'],
                              capture_output=True, text=True, check=True)
        self.assertIn('--user-confirmations', done.stdout)
        self.assertIn('--release-authorized', done.stdout)

    def exercise(self, has_confirmation):
        with tempfile.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            pkg = t / 'package'
            pkg.mkdir()
            out = t / 'results'
            confirmation_file = t / 'user-confirmations.json'
            confirmation_file.write_text(json.dumps({'purpose':'USER_DIRECT_FORM_CONFIRMATION_NOT_IMAGE_OBSERVATION',
               'confirmations':[{'imageId':'IMG-0001'}]}), encoding='utf-8')
            records = t / 'records.json'
            records.write_text('{}', encoding='utf-8')
            values = {'inputImageCount':1, 'images':[{'id':'IMG-0001'}]}
            def fake_load(file):
                if pathlib.Path(file).name=='INPUT_MANIFEST.json': return values
                return {'decisions':[{'imageId':'IMG-0001'}]}
            def fake_audit(package_dir, records_path, observations_path, *, allow_release, user_confirmations_path):
                self.assertTrue(allow_release)
                self.assertEqual(pathlib.Path(records_path), records)
                self.assertEqual(user_confirmations_path, confirmation_file if has_confirmation else None)
                return {'total':1,'hardConflicts':[],
                        'identityReviewRecommendations':[] if user_confirmations_path else ['IMG-0001'],
                        'speciesAutoChanges':0,'candidateRemovalsByNumeric':0}
            csv_bytes = b'nickname,species\nsample,form\n'
            sample_binding = {'csvSHA256': hashlib.sha256(csv_bytes).hexdigest(), 'includedCount':1, 'rows':[{'imageId':'IMG-0001'}]}
            with patch.object(release,'release_preflight',return_value=({'sourceCommit':'a'*40},{'schemaVersion':'release-evidence-v0.1'})), \
                 patch.object(release,'load_json',side_effect=fake_load), \
                 patch.object(release,'audit',side_effect=fake_audit) as called, \
                 patch.object(release,'build',return_value=(csv_bytes,{'included':1,'excluded':0})), \
                 patch.object(release,'make_binding',return_value=sample_binding):
                if has_confirmation:
                    result = release.run(pkg,records,None,out,evidence_file=t/'unused.json',
                                         explicit_release=True,user_confirmations_path=confirmation_file)
                    self.assertEqual(result['status'], 'PASS')
                    self.assertTrue((out/'pokesleep_import.csv').exists())
                    self.assertTrue((out/'RELEASE_ROW_BINDING.json').exists())
                    self.assertTrue((out/'RELEASE_GATE_STATUS.json').exists())
                else:
                    with self.assertRaisesRegex(ValueError, 'SpeciesAudit conflict'):
                        release.run(pkg,records,None,out,evidence_file=t/'unused.json',
                                    explicit_release=True)
                    self.assertFalse((out/'pokesleep_import.csv').exists())
                    self.assertFalse((out/'RELEASE_GATE_STATUS.json').exists())
                self.assertEqual(called.call_count,1)

    def test_user_confirmation_propagates_with_release_opt_in(self):
        self.exercise(True)

    def test_no_confirmation_preserves_strict_review_hold(self):
        self.exercise(False)

if __name__=='__main__':
    unittest.main()
