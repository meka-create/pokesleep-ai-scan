"""Synthetic/structural gate integration. NO assertion of real screenshot recognition."""
import tempfile,unittest,json,shutil,sys,hashlib
from pathlib import Path
from PIL import Image
R=Path(__file__).resolve().parent.parent/'kit-assets';sys.path.insert(0,str(R))
from PROTOTYPE_EXPORT_GATE import run,EXPORT_NAME,BINDING_NAME,STATUS_NAME
class GateTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.dir=Path(self.tmp.name)
  pkg=self.dir/'pkg';pkg.mkdir();(pkg/'images').mkdir()
  for x in R.iterdir():
   if x.is_file():shutil.copy(x,pkg/x.name)
  image=pkg/'images'/'IMG-0001.png';Image.new('RGB',(12,12),(16,80,144)).save(image)
  manifest={'schemaVersion':'ai-input-manifest-v0.1','kitVersion':'0.12.0-prototype',
        'images':[{'id':'IMG-0001','path':'images/IMG-0001.png',
                   'originalFilename':'SYNTHETIC_TEST_IMAGE.png','size':image.stat().st_size,
                   'sha256':hashlib.sha256(image.read_bytes()).hexdigest()}],
        'inputImageCount':1,'sourceSelectedCount':1,'duplicatePolicy':'user-selected-keep-all'}
  (pkg/'INPUT_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False))
  data={'nickname':'SYNTHETIC-NOT-REAL','species':'バケッチャ (ちゅうだましゅ)',
        'level':16,'skillLevel':1,'foods':['ずっしりカボチャ']*3,
        'mainSkill':'エナジーチャージS','nature':'きまぐれ',
        'subskills':['おてつだいボーナス','睡眠EXPボーナス','食材確率アップM','おてつだいスピードM','スキル確率アップS'],
        'sleepTogetherHours':0,'shiny':0,'fieldEvidence':{'sleepTogetherHours':'user-policy-default','shiny':'user-policy-default'}}
  records={'schemaVersion':'ai-reading-v0.1','kitVersion':'0.12.0-prototype',
        'decisions':[{'imageId':'IMG-0001','decision':'include','data':data,'unresolved':[],'reviewComplete':True}]}
  self.pkg=pkg;self.records=self.dir/'records.json';self.records.write_text(json.dumps(records,ensure_ascii=False))
  obs={'purpose':'READ_ONLY_AUDIT_NOT_GOLD','imageObservations':[{'imageId':'IMG-0001','speciesFamilyVisualConfirmed':True}]}
  self.obs=self.dir/'obs.json';self.obs.write_text(json.dumps(obs,ensure_ascii=False))
  confirmed={'purpose':'USER_DIRECT_FORM_CONFIRMATION_NOT_IMAGE_OBSERVATION',
    'confirmations':[{'imageId':'IMG-0001','originalFilename':'SYNTHETIC_TEST_IMAGE.png',
      'speciesFamily':'バケッチャ','confirmedSize':'ちゅうだましゅ','userAnswerText':'2',
      'responseOrigin':'direct-user-reply'}]}
  self.conf=self.dir/'conf.json';self.conf.write_text(json.dumps(confirmed,ensure_ascii=False))
  self.output=self.dir/'dev'
 def exported(self):return all((self.output/name).is_file() for name in (EXPORT_NAME,BINDING_NAME,STATUS_NAME))
 def test_user_answer_gate_pass_no_release(self):
  status=run(self.pkg,self.records,self.obs,self.output,True,user_confirmations_path=self.conf)
  self.assertEqual(status['included'],1);self.assertFalse(status['productionCsvAllowed']);self.assertTrue(self.exported())
  self.assertEqual(status['userFormConfirmationCount'],1)
  self.assertEqual(status['userFormConfirmations'][0]['confirmedSize'],'ちゅうだましゅ')
 def test_without_user_answer_hold_and_no_outputs(self):
  with self.assertRaisesRegex(ValueError,'SPECIES_IDENTITY_REVIEW_HOLD'):
   run(self.pkg,self.records,self.obs,self.output,True)
  self.assertFalse(self.exported())
 def test_mismatched_answer_must_not_override(self):
  x=json.loads(self.conf.read_text());x['confirmations'][0]['confirmedSize']='おおだましゅ';x['confirmations'][0]['userAnswerText']='3'
  self.conf.write_text(json.dumps(x,ensure_ascii=False))
  with self.assertRaisesRegex(ValueError,'different form'):
   run(self.pkg,self.records,self.obs,self.output,True,user_confirmations_path=self.conf)
  self.assertFalse(self.exported())
 def test_user_reply_not_evolution_visual(self):
  x=json.loads(self.obs.read_text());x['imageObservations'][0]['speciesFamilyVisualConfirmed']=None
  self.obs.write_text(json.dumps(x,ensure_ascii=False))
  with self.assertRaisesRegex(ValueError,'species FAMILY'):
   run(self.pkg,self.records,self.obs,self.output,True,user_confirmations_path=self.conf)
  self.assertFalse(self.exported())
 def test_production_remains_hold(self):
  with self.assertRaisesRegex(ValueError,'Production remains HOLD'):
   run(self.pkg,self.records,self.obs,self.output,False,user_confirmations_path=self.conf)
  self.assertFalse(self.exported())
if __name__=='__main__':unittest.main(verbosity=2)

class InGameEightFormGateTest(unittest.TestCase):
 exported=GateTest.exported
 def setUp(self):
  GateTest.setUp(self)
  rec=json.loads(self.records.read_text())
  rec['decisions'][0]['data']['species']='バケッチャ (おおだましゅ)'
  self.records.write_text(json.dumps(rec,ensure_ascii=False))
  obs=json.loads(self.obs.read_text());obs['imageObservations'][0]['speciesFamilyVisualConfirmed']=None
  self.obs.write_text(json.dumps(obs,ensure_ascii=False))
  c=json.loads(self.conf.read_text());c['confirmations'][0].update({
   'confirmedSize':'おおだましゅ', 'userAnswerText':'3',
   'verificationSource':'in-game-details','questionScope':'eight-form'})
  self.conf.write_text(json.dumps(c,ensure_ascii=False))
 def test_game_stage_and_form_reply_allows_prototype_only(self):
  status=run(self.pkg,self.records,self.obs,self.output,True,user_confirmations_path=self.conf)
  self.assertEqual(status['included'],1)
  self.assertIs(status['productionCsvAllowed'],False)
  self.assertIs(status['compatibilityVerified'],False)
  self.assertEqual(status['userFormConfirmations'][0]['verificationSource'],'in-game-details')
  self.assertTrue(self.exported())
 def test_user_answer_without_game_attestation_does_not_bypass_stage_hold(self):
  c=json.loads(self.conf.read_text());c['confirmations'][0].pop('verificationSource')
  self.conf.write_text(json.dumps(c,ensure_ascii=False))
  with self.assertRaises(ValueError):
   run(self.pkg,self.records,self.obs,self.output,True,user_confirmations_path=self.conf)
  self.assertFalse(self.exported())
 def test_user_answer_wrong_form_does_not_publish(self):
  c=json.loads(self.conf.read_text());c['confirmations'][0]['confirmedSize']='こだましゅ'
  self.conf.write_text(json.dumps(c,ensure_ascii=False))
  with self.assertRaises(ValueError):
   run(self.pkg,self.records,self.obs,self.output,True,user_confirmations_path=self.conf)
  self.assertFalse(self.exported())


class CrossStageConflictGateTest(unittest.TestCase):
 exported=GateTest.exported
 def setUp(self):
  GateTest.setUp(self)
  rec=json.loads(self.records.read_text())
  rec['decisions'][0]['data'].update({
   'species':'パンプジン (こだましゅ)',
   'nature':'うっかりや',
   'subskills':['きのみの数S','おてつだいスピードM','食材確率アップM','最大所持数アップM','最大所持数アップS']})
  self.records.write_text(json.dumps(rec,ensure_ascii=False))
  obs={'purpose':'READ_ONLY_AUDIT_NOT_GOLD','imageObservations':[{
    'imageId':'IMG-0001','helpSeconds':5335,'carry':15,
    'carryVisualConfirmed':True,'speciesFamilyVisualConfirmed':True,
    'formSizeVisualConfirmed':True,'speciesVisualConfirmed':True}]}
  self.obs.write_text(json.dumps(obs,ensure_ascii=False))
 def test_strong_cross_stage_numeric_disagreement_forces_hold(self):
  with self.assertRaisesRegex(ValueError,'SPECIES_IDENTITY_REVIEW_HOLD'):
   run(self.pkg,self.records,self.obs,self.output,True)
  self.assertFalse(self.exported())
 def test_explicit_eight_option_in_game_reconfirmation_can_clear_hold(self):
  confirmed={'purpose':'USER_DIRECT_FORM_CONFIRMATION_NOT_IMAGE_OBSERVATION',
  'confirmations':[{'imageId':'IMG-0001','originalFilename':'SYNTHETIC_TEST_IMAGE.png',
      'speciesFamily':'パンプジン','confirmedSize':'こだましゅ',
      'userAnswerText':'5','responseOrigin':'direct-user-reply',
      'verificationSource':'in-game-details','questionScope':'eight-form'}]}
  self.conf.write_text(json.dumps(confirmed,ensure_ascii=False))
  stat=run(self.pkg,self.records,self.obs,self.output,True,user_confirmations_path=self.conf)
  self.assertEqual(stat['included'],1)
  self.assertEqual(stat['userFormConfirmationCount'],1)
  self.assertFalse(stat['productionCsvAllowed'])
  self.assertTrue(self.exported())
