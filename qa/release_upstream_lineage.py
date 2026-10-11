"""Independent frozen-master lineage audit against an actual pinned upstream Git checkout."""
import json, pathlib, sys
root=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'trusted_tools/scripts'))
from sync_upstream import project
master=json.loads((root/'release-kit-assets/MASTER_DATA.json').read_text())
ver=json.loads((root/'release-kit-assets/KIT_VERSION.json').read_text())
site=root/'upstream_verification'
source_head=(site/'.git/HEAD').read_text().strip()
import subprocess
commit=subprocess.check_output(['git','-C',str(site),'rev-parse','HEAD'],text=True).strip()
assert commit==ver['sourceCommit'],('UPSTREAM_PIN_MISMATCH',commit,ver['sourceCommit'])
candidate,diff=project(site,master)
expected={'addedSpecies':[],'removedSpecies':[],'changedSpecies':{},
 'newIngredientKeys':[],'removedIngredientKeys':[],'changedIngredientTranslations':{},
 'newSubskillKeys':[],'removedSubskillKeys':[],'changedSubskillTranslations':{},
 'newNatureKeys':[],'removedNatureKeys':[],'changedNatureTranslations':{}}
for key,want in expected.items():
    assert diff.get(key)==want,('SOURCE_MASTER_DIVERGENCE',key,diff.get(key))
assert len(candidate['pokemon'])==len(master['pokemon'])==249
assert diff['sourceCommit']==ver['sourceCommit']
print('PASS: legacy master matches pinned actual upstream source commit exactly for species, food, natures, subskills')
