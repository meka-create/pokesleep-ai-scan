"""Code-based safety regressions, not claims of AI visual reading accuracy."""
from pathlib import Path
import json,sys,tempfile,unittest,copy
R=Path(__file__).resolve().parent.parent/'kit-assets'
sys.path.insert(0,str(R))
from SPECIES_AUDIT import (audit_record, read_user_form_confirmations, verify_bundle,
                            confirmed_four_size_by_lower_bound, audit)
M=json.loads((R/'MASTER_DATA.json').read_text(encoding='utf-8'))
P={p['name']:p for p in M['pokemon']}

base={'species':'バケッチャ (ちゅうだましゅ)','foods':['ずっしりカボチャ']*3,
      'mainSkill':'エナジーチャージS','level':16,'nature':'きまぐれ',
      'subskills':['おてつだいボーナス','睡眠EXPボーナス','食材確率アップM','おてつだいスピードM','スキル確率アップS']}
def exam(obs=None,confirm=None,species=None):
    d=copy.deepcopy(base)
    if species:d['species']=species
    return audit_record(M,{'imageId':'IMG-0085','decision':'include','data':d},obs or {},confirm)
class FourSizeConfirmationTests(unittest.TestCase):
    def test_expected_carry11_requires_confirmation(self):
        self.assertTrue(exam({'carry':11,'carryVisualConfirmed':True})['speciesIdentityReviewRecommended'])
    def test_user_answer_closes_form_review_without_visual_forgery(self):
        conf={'speciesFamily':'バケッチャ','confirmedSize':'ちゅうだましゅ',
              'originalFilename':'Screenshot_20261008-004636.png','userAnswerText':'2'}
        result=exam({'speciesFamilyVisualConfirmed':True},conf)
        self.assertFalse(result['speciesIdentityReviewRecommended'])
        self.assertEqual(result['formSizeEvidenceSource'],'USER_DIRECT_REPLY')
        self.assertIsNone(result['speciesVisualConfirmed'])
        self.assertEqual(result['userFormConfirmation']['source'],'USER_DIRECT_REPLY_NOT_IMAGE_VISUAL')
    def test_family_not_verified_must_hold(self):
        c={'speciesFamily':'バケッチャ','confirmedSize':'ちゅうだましゅ','originalFilename':'x','userAnswerText':'2'}
        with self.assertRaisesRegex(ValueError,'species FAMILY'):
            exam({},c)
    def test_conflicting_user_reply_is_hold(self):
        c={'speciesFamily':'バケッチャ','confirmedSize':'おおだましゅ','originalFilename':'x','userAnswerText':'3'}
        with self.assertRaisesRegex(ValueError,'different form'):
            exam({'speciesFamilyVisualConfirmed':True},c)
    def test_form_visual_without_family_is_hold(self):
        self.assertTrue(exam({'formSizeVisualConfirmed':True})['speciesIdentityReviewRecommended'])
    def test_form_visual_with_family_is_accepted(self):
        v=exam({'formSizeVisualConfirmed':True,'speciesFamilyVisualConfirmed':True})
        self.assertFalse(v['speciesIdentityReviewRecommended'])
    def test_carry_below_minimum_cannot_be_silent_user_override(self):
        c={'speciesFamily':'バケッチャ','confirmedSize':'ちゅうだましゅ','originalFilename':'x','userAnswerText':'2'}
        r=exam({'speciesFamilyVisualConfirmed':True,'carry':7,'carryVisualConfirmed':True},c)
        self.assertTrue(r['speciesIdentityReviewRecommended'])
        self.assertTrue(r['possibleCarryBelowMinimumNeedsReview'])
    def test_old_lower_bound_still_safe(self):
        r=exam({'carry':7,'carryVisualConfirmed':True},species='バケッチャ (こだましゅ)')
        self.assertFalse(r['speciesIdentityReviewRecommended'])
        self.assertEqual(r['formSizeEvidenceSource'],'VISIBLE_CARRY_LOWER_BOUND')
    def test_sp_not_used_to_auto_confirm(self):
        self.assertTrue(exam({'sp':99999})['speciesIdentityReviewRecommended'])
    def test_evolution_visual_verification_required(self):
        for species in ('ジュプトル','ジュカイン','ラッキー','ハピナス'):
            d=copy.deepcopy(base);p=P[species]
            d.update({'species':species,'foods':[p['ing1']['name']]*3,'mainSkill':p['mainSkill']})
            v=audit_record(M,{'imageId':'IMG-001','decision':'include','data':d},{})
            self.assertTrue(v['speciesIdentityReviewRecommended'],species)
            v=audit_record(M,{'imageId':'IMG-001','decision':'include','data':d},{'speciesVisualConfirmed':True})
            self.assertFalse(v['highRiskEvolutionVisualReviewRecommended'],species)
    def test_form_source_not_species_visual_proof(self):
        r=exam({'speciesVisualConfirmed':True})
        self.assertTrue(r['speciesIdentityReviewRecommended'])
    def test_form_confirmation_parser_accepts_direct_answer_and_rejects_wrong_id_name(self):
        im={'id':'IMG-0085','originalFilename':'Screenshot_20261008-004636.png'}
        data={'purpose':'USER_DIRECT_FORM_CONFIRMATION_NOT_IMAGE_OBSERVATION',
              'confirmations':[{'imageId':im['id'],'originalFilename':im['originalFilename'],
               'speciesFamily':'バケッチャ','confirmedSize':'ちゅうだましゅ',
               'userAnswerText':'2','responseOrigin':'direct-user-reply'}]}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'forms.json'
            path.write_text(json.dumps(data,ensure_ascii=False))
            self.assertEqual(len(read_user_form_confirmations(path,{'images':[im]})),1)
            for key,bad in [('imageId','IMG-0086'),('originalFilename','other.png'),
                            ('responseOrigin','ai-guess'),('userAnswerText','9'),('confirmedSize','ギガだましゅ')]:
                x=copy.deepcopy(data);x['confirmations'][0][key]=bad
                path.write_text(json.dumps(x,ensure_ascii=False))
                with self.assertRaises(ValueError,msg=(key,bad)):
                    read_user_form_confirmations(path,{'images':[im]})
    def test_master_and_release_hold(self):
        master,version=verify_bundle(R)
        self.assertEqual(len(master['pokemon']),249)
        self.assertIs(version['productionCsvAllowed'],False)
        self.assertIs(version['compatibilityVerified'],False)
        self.assertIs(version['masterVerifiedAgainstLive'],False)
    def test_pin_all_assets(self):
        import hashlib
        version=json.loads((R/'KIT_VERSION.json').read_text())
        for name,hash_ in version['rawAssetSha256'].items():
            self.assertEqual(hashlib.sha256((R/name).read_bytes()).hexdigest(),hash_,name)

if __name__=='__main__':unittest.main(verbosity=2)
