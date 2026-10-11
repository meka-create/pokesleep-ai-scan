"""Synthetic numeric evidence; do NOT treat these tests as genuine AI image-read accuracy."""
import unittest,sys,json,copy,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent/'kit-assets'
sys.path.insert(0,str(ROOT))
from SPECIES_AUDIT import four_size_numeric_advisory, read_user_form_confirmations, audit_record
from numeric_observer import observed_numeric
M=json.loads((ROOT/'MASTER_DATA.json').read_text(encoding='utf-8'))
ALL=[p['name'] for p in M['pokemon'] if p['name'].startswith(('バケッチャ (','パンプジン ('))]
BASE={'species':'パンプジン (こだましゅ)', 'foods':['ずっしりカボチャ','ずっしりカボチャ','ほっこりポテト'],
      'mainSkill':'エナジーチャージS','level':16,'nature':'うっかりや',
      'subskills':['きのみの数S','おてつだいスピードM','食材確率アップM','最大所持数アップM','最大所持数アップS']}

class AdvisoryTest(unittest.TestCase):
 def get(self,obs):
  rec={**BASE,**obs}
  numeric={s:observed_numeric(s,M,rec) for s in ALL}
  return four_size_numeric_advisory(BASE['species'],ALL,numeric,obs)
 def test_wrong_stage_cross_check_finds_pumpkaboo_large(self):
  r=self.get({'helpSeconds':5335,'carry':15})
  self.assertEqual(r['suggestedSpecies'],'バケッチャ (おおだましゅ)')
  self.assertTrue(r['evolutionStageRecheckRequired'])
  self.assertTrue(r['suggestionDiffersFromReportedSpecies'])
  self.assertEqual(len(r['allOptions']),8)
  self.assertTrue(r['neverAutoConfirmOrDiscardCandidates'])
 def test_carry_only_does_not_claim_probability(self):
  r=self.get({'carry':15})
  self.assertEqual(r['status'],'TIED_PREFERRED_CANDIDATES_NOT_CONFIRMED')
  self.assertIsNone(r['suggestedSpecies'])
  self.assertTrue(r['notCalibratedProbability'])
 def test_no_observations_cannot_fabricate_favorite(self):
  r=self.get({})
  self.assertIsNone(r['suggestedSpecies'])
  self.assertEqual(r['status'],'NOT_ENOUGH_VISIBLE_NUMERIC_DATA')
 def test_unmatched_both_values_never_rank_single_evidence(self):
  r=self.get({'helpSeconds':9999999,'carry':15})
  self.assertIsNone(r['suggestedSpecies'])
  self.assertEqual(r['status'],'NO_SUPPORTED_NUMERIC_FAVORITE')
 def test_not_a_form_no_advisory(self):
  r=four_size_numeric_advisory('ピカチュウ',['ピカチュウ'],{}, {'carry':17})
  self.assertIsNone(r)
 def test_audit_output_does_not_mutate_user_record(self):
  d=copy.deepcopy(BASE)
  r=audit_record(M,{'imageId':'SYNTHETIC','decision':'include','data':d},{'helpSeconds':5335,'carry':15})
  self.assertEqual(d['species'],'パンプジン (こだましゅ)')
  self.assertTrue(r['speciesIdentityReviewRecommended'])
  self.assertEqual(r['fourSizeNumericAdvisory']['suggestedSpecies'],'バケッチャ (おおだましゅ)')
 def test_user_game_full_answer_can_confirm_stage_without_image_flag(self):
  data=copy.deepcopy(BASE);data['species']='バケッチャ (おおだましゅ)'
  c={'speciesFamily':'バケッチャ','confirmedSize':'おおだましゅ',
     'originalFilename':'SYNTHETIC.png','userAnswerText':'バケッチャ (おおだましゅ)',
     'verificationSource':'in-game-details'}
  r=audit_record(M,{'imageId':'SYNTHETIC','decision':'include','data':data},{},c)
  self.assertFalse(r['speciesIdentityReviewRecommended'])
  self.assertEqual(r['formSizeEvidenceSource'],'USER_DIRECT_IN_GAME_STAGE_AND_SIZE')
  self.assertIsNone(r['speciesVisualConfirmed'])
  self.assertTrue(r['userFormConfirmation']['verificationSource']=='in-game-details')
 def test_numeric_guess_alone_still_hold(self):
  d=copy.deepcopy(BASE); d['species']='バケッチャ (おおだましゅ)'
  r=audit_record(M,{'imageId':'SYNTHETIC','decision':'include','data':d},{'helpSeconds':5335,'carry':15})
  self.assertTrue(r['speciesIdentityReviewRecommended'])
 def test_japanese_fullwidth_form_name_user_reply(self):
  manifest={'images':[{'id':'SYNTHETIC','originalFilename':'SYNTHETIC.png'}]}
  c={'imageId':'SYNTHETIC','originalFilename':'SYNTHETIC.png',
     'speciesFamily':'バケッチャ','confirmedSize':'おおだましゅ',
     'userAnswerText':'バケッチャ（おおだましゅ）','responseOrigin':'direct-user-reply',
     'verificationSource':'in-game-details','questionScope':'eight-form'}
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'confirm.json'
   path.write_text(json.dumps({'purpose':'USER_DIRECT_FORM_CONFIRMATION_NOT_IMAGE_OBSERVATION',
                               'confirmations':[c]},ensure_ascii=False))
   self.assertEqual(len(read_user_form_confirmations(path,manifest)),1)
  record=copy.deepcopy(BASE);record['species']='バケッチャ (おおだましゅ)'
  result=audit_record(M,{'imageId':'SYNTHETIC','decision':'include','data':record},{},c)
  self.assertEqual(result['formSizeEvidenceSource'],'USER_DIRECT_IN_GAME_STAGE_AND_SIZE')
 def test_eight_choice_3_is_pumpkaboo_large(self):
  c={'imageId':'SYNTHETIC','originalFilename':'SYNTHETIC.png',
     'speciesFamily':'バケッチャ','confirmedSize':'おおだましゅ',
     'userAnswerText':'3','responseOrigin':'direct-user-reply',
     'verificationSource':'in-game-details','questionScope':'eight-form'}
  manifest={'images':[{'id':'SYNTHETIC','originalFilename':'SYNTHETIC.png'}]}
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'confirm.json'
   def check(c0,ok):
    p.write_text(json.dumps({'purpose':'USER_DIRECT_FORM_CONFIRMATION_NOT_IMAGE_OBSERVATION','confirmations':[c0]},ensure_ascii=False))
    if ok: self.assertEqual(len(read_user_form_confirmations(p,manifest)),1)
    else:
     with self.assertRaises(ValueError):read_user_form_confirmations(p,manifest)
   check(c,True)
   for patch in ({'confirmedSize':'ギガだましゅ'},
                 {'verificationSource':None},{'userAnswerText':'9'},{'originalFilename':'bad.png'}):
    check({**c,**patch},False)
 def test_all_form_matches_remain_not_user_confirmed(self):
  r=self.get({'helpSeconds':5335,'carry':15})
  self.assertTrue(r['neverAutoConfirmOrDiscardCandidates'])
  self.assertFalse(r.get('formSizeVisualConfirmed',False))

class CrossStageMismatchRegression(unittest.TestCase):
 def test_img0085_pattern_blocks_even_if_ai_claimed_visual_size(self):
  # Synthetic reproduction of the numerics; not proof of image recognition.
  record=copy.deepcopy(BASE)
  obs={'helpSeconds':5335,'carry':15,'carryVisualConfirmed':True,
       'speciesVisualConfirmed':True,'speciesFamilyVisualConfirmed':True,
       'formSizeVisualConfirmed':True}
  report=audit_record(M,{'imageId':'IMG-0085','decision':'include','data':record},obs)
  self.assertEqual(report['fourSizeNumericAdvisory']['suggestedSpecies'],'バケッチャ (おおだましゅ)')
  self.assertTrue(report['strongCrossStageNumericConflictNeedsReview'])
  self.assertTrue(report['speciesIdentityReviewRecommended'])
  self.assertFalse(report['strongCrossStageNumericConflictResolvedByUser'])

 def test_in_game_confirmation_can_resolve_contradiction_without_numeric_autocorrect(self):
  record=copy.deepcopy(BASE)
  obs={'helpSeconds':5335,'carry':15,'carryVisualConfirmed':True,
       'speciesFamilyVisualConfirmed':True,'formSizeVisualConfirmed':True}
  confirmed={'imageId':'IMG-0085','originalFilename':'Screenshot_20261008-004636.png',
       'speciesFamily':'パンプジン','confirmedSize':'こだましゅ',
       'userAnswerText':'パンプジン (こだましゅ)','responseOrigin':'direct-user-reply',
       'verificationSource':'in-game-details','questionScope':'eight-form'}
  report=audit_record(M,{'imageId':'IMG-0085','decision':'include','data':record},obs,confirmed)
  self.assertTrue(report['strongCrossStageNumericConflictNeedsReview'])
  self.assertTrue(report['strongCrossStageNumericConflictResolvedByUser'])
  self.assertFalse(report['speciesIdentityReviewRecommended'])
  self.assertEqual(report['reportedSpecies'],'パンプジン (こだましゅ)')

 def test_partial_numeric_evidence_cannot_create_strong_stage_conflict(self):
  record=copy.deepcopy(BASE)
  report=audit_record(M,{'imageId':'IMG-0085','decision':'include','data':record},
                      {'carry':15,'formSizeVisualConfirmed':True,'speciesFamilyVisualConfirmed':True})
  self.assertFalse(report['strongCrossStageNumericConflictNeedsReview'])

if __name__=='__main__':unittest.main(verbosity=2)
