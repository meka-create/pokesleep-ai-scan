"""Verify six translation-only labels never become false positive updates."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.github/monitor'))
sys.path.insert(0,str(ROOT/'tests'))
from master_diff import compare,selectable_subskill_keys
from test_upstream_sync import UpstreamSyncTests

class TestMonitorSubskillSelection(unittest.TestCase):
 def setUp(self):
  self.fx=UpstreamSyncTests();self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.legacy=self.fx.legacy

 def upstream(self):
  s=self.fx.src
  return {'pokemon':json.loads((s/'data/pokemon.json').read_text()),
    'pokemonsJa':json.loads((s/'i18n/ja/pokemons.json').read_text()),
    'dataJa':json.loads((s/'i18n/ja/data.json').read_text()),
    'skillsJa':json.loads((s/'i18n/ja/skills.json').read_text()),
    'subskillType':(s/'util/SubSkill.ts').read_text()}

 def test_six_display_only_subskill_headings_are_ignored(self):
  self.fx.data['subskill'].update({'Gold colored':'金色サブスキル','Skill Level Up':'スキルレベルアップ',
  'Skill Trigger':'スキル確率アップ','Helping Speed':'おてつだいスピード',
  'Ingredient Finder':'食材確率アップ','Inventory Up':'最大所持数アップ'})
  self.fx.write()
  result=compare(self.legacy,self.upstream(),{},'a'*40)
  self.assertEqual(result['status'],'SOURCE_PROJECTION_MATCH_HOLD')
  self.assertEqual(result['summary']['changedTranslations'],0)
  self.assertEqual(len(selectable_subskill_keys(self.upstream()['subskillType'])),17)

 def test_new_selectable_subskill_detected(self):
  self.fx.active_subskills.append('Future Selectable')
  self.fx.data['subskill']['Future Selectable']='未来の選択可能サブスキル'
  self.fx.write()
  result=compare(self.legacy,self.upstream(),{},'a'*40)
  self.assertEqual(result['status'],'DIFFERENCES_FOUND_HOLD')
  self.assertTrue(any(x['domain']=='subskills' and x['key']=='Future Selectable' for x in result['translationDifferences']))

 def test_existing_selectable_translation_change_detected(self):
  old=self.fx.active_subskills[0]
  self.fx.data['subskill'][old]+='【変更】';self.fx.write()
  self.assertEqual(compare(self.legacy,self.upstream(),{},'a'*40)['status'],'DIFFERENCES_FOUND_HOLD')

 def test_unrecognized_enum_fails_closed(self):
  upstream=self.upstream();upstream['subskillType']='export const changed = true;'
  with self.assertRaisesRegex(ValueError,'Unknown selectable subskill'):
   compare(self.legacy,upstream,{},'a'*40)

 def test_broken_translation_fails_closed(self):
  old=self.fx.active_subskills[0];self.fx.data['subskill'].pop(old);self.fx.write()
  with self.assertRaisesRegex(ValueError,'lacks Japanese translation'):
   compare(self.legacy,self.upstream(),{},'a'*40)

if __name__=='__main__':unittest.main()
