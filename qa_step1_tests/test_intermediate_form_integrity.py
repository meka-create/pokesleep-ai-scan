"""Midpoint regression: provenance stays aligned to exactly the CSV-eligible row."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'kit-assets'))
from SPECIES_AUDIT import audit
from test_gate_integration import GateTest

class ConfirmationIntegrity(unittest.TestCase):
    def setUp(self):
        self.f=GateTest('test_user_answer_gate_pass_no_release')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
    def test_excluded_row_must_not_silently_consume_user_confirmation(self):
        payload=json.loads(self.f.records.read_text())
        payload['decisions'][0]['decision']='exclude'
        self.f.records.write_text(json.dumps(payload,ensure_ascii=False))
        with self.assertRaisesRegex(ValueError,'excluded|non-included|include'):
            audit(self.f.pkg,self.f.records,self.f.obs,user_confirmations_path=self.f.conf)
    def test_invalid_decision_is_not_treated_as_exclusion(self):
        payload=json.loads(self.f.records.read_text())
        payload['decisions'][0]['decision']='unrecognized-status'
        self.f.records.write_text(json.dumps(payload,ensure_ascii=False))
        with self.assertRaisesRegex(ValueError,'invalid image decision'):
            audit(self.f.pkg,self.f.records,self.f.obs)
    def test_standalone_audit_exits_hold_on_unresolved_size(self):
        output=self.f.dir/'audit.json'
        p=subprocess.run([sys.executable,str(ROOT/'kit-assets/SPECIES_AUDIT.py'),
             '--package-dir',str(self.f.pkg),'--records',str(self.f.records),
             '--observations',str(self.f.obs),'--output',str(output)],
             capture_output=True,text=True)
        self.assertEqual(p.returncode,3,p.stdout+'\n'+p.stderr)
        self.assertTrue(output.is_file())
        self.assertEqual(json.loads(output.read_text())['identityReviewRecommendations'],['IMG-0001'])
    def test_standalone_audit_succeeds_after_valid_confirmation(self):
        output=self.f.dir/'audit_pass.json'
        p=subprocess.run([sys.executable,str(ROOT/'kit-assets/SPECIES_AUDIT.py'),
             '--package-dir',str(self.f.pkg),'--records',str(self.f.records),
             '--observations',str(self.f.obs),'--user-confirmations',str(self.f.conf),
             '--output',str(output)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        self.assertEqual(json.loads(output.read_text())['userFormConfirmationCount'],1)

if __name__=='__main__':unittest.main()
