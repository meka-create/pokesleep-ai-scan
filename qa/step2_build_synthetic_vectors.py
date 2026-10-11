#!/usr/bin/env python3
"""Generate synthetic test CSVs from the frozen current master; never use user or Golden data.

Every test row must be permitted by the current 16-column Validator contract.
Importer E2E is executed separately against the real published pokesleep-tool UI.
"""
import csv
import json
import pathlib
import hashlib
from collections import Counter

ROOT=pathlib.Path(__file__).resolve().parents[1]
MASTER=json.loads((ROOT/'kit-assets/MASTER_DATA.json').read_text(encoding='utf-8'))
SCHEMA=json.loads((ROOT/'kit-assets/CSV_SCHEMA.json').read_text(encoding='utf-8'))
OUT=ROOT/'step2_evidence'/'fixtures'
OUT.mkdir(parents=True,exist_ok=True)
HEADER=SCHEMA['header']
assert len(HEADER)==16
NATURES={s['ja'] for s in MASTER['natures']}
SKILLS=[s['ja'] for s in MASTER['subskills']]
FOODS=set(MASTER['ingredients'].values())
POKEMON=MASTER['pokemon']
assert len(POKEMON)>=249 and len(SKILLS)==17 and len(NATURES)==25

def slots(p,slot):
    result=[]
    for i in range(1,slot+1):
        item=p.get('ing'+str(i))
        if item and item.get('c'+str(slot),0) and item['name'] in FOODS:
            result.append(item['name'])
    for item in p.get('mythIng',[]):
        if item.get('c'+str(slot),0) and item['name'] in FOODS:
            result.append(item['name'])
    return list(dict.fromkeys(result))

def row(p,i,prefix='検証', *, variant=False, explicit_name=None):
    name=p['name']
    nature='がんばりや'
    if name=='ストリンダー (ロー)': nature='まじめ'
    main=p['mainSkill']
    if name=='ミュウ':
        main=SCHEMA['mewVersatileCsvLabels']['Berry Burst']
    selected=[]
    for sl in (1,2,3):
        candidates=slots(p,sl)
        assert candidates,(name,sl)
        selected.append(candidates[(i+sl-1)%len(candidates)] if variant else candidates[0])
    abilities=[SKILLS[(i+j)%len(SKILLS)] for j in range(5)]
    nickname=explicit_name if explicit_name is not None else f'{prefix}{i:03d}'
    values=[nickname,name, 60 if variant else 30, 3 if variant else 1, *selected, main,
            nature, *abilities, 0, 0]
    assert len(values)==16
    assert len(set(abilities))==5
    return values

def emit(filename,rows):
    path=OUT/filename
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.writer(f,lineterminator='\n')
        writer.writerow(HEADER)
        writer.writerows(rows)
    with path.open('r',encoding='utf-8',newline='') as f:
        data=list(csv.reader(f,strict=True))
    assert data[0]==HEADER and len(data)==len(rows)+1 and all(len(r)==16 for r in data)
    return {'file':str(path.relative_to(ROOT)), 'rows':len(rows),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'species':len({r[1] for r in data[1:]})}

emit_results={}
emit_results['smoke']=emit('01_smoke.csv',[row(POKEMON[0],0)])
regular=[p for p in POKEMON if p['name'] not in ('ミュウ','ダークライ')]
emit_results['standard']=emit('02_standard_twelve.csv',[row(p,i,variant=True) for i,p in enumerate(regular[:12])])
special=[p for p in POKEMON if p['name'] in ('ミュウ','ダークライ') or '(' in p['name']]
emit_results['forms']=emit('03_forms_and_mythical.csv',[row(p,i,variant=True) for i,p in enumerate(special)])
emit_results['all']=emit('04_all_master_species.csv',[row(p,i,variant=True) for i,p in enumerate(POKEMON)])
emit_results['subskills']=emit('05_all_subskill_words.csv',[row(regular[i],i,variant=True) for i in range(len(SKILLS))])
emit_results['mew']=emit('07_mew_alone.csv',[row(next(p for p in POKEMON if p['name']=='ミュウ'),0,variant=True)])
emit_results['darkrai']=emit('08_darkrai_alone.csv',[row(next(p for p in POKEMON if p['name']=='ダークライ'),0,variant=True)])
emit_results['toxtricity']=emit('09_toxtricity_forms.csv',[row(p,i,variant=True) for i,p in enumerate(POKEMON) if p['name'].startswith('ストリンダー (')])
emit_results['pumpkin']=emit('10_pumpkin_forms.csv',[row(p,i,variant=True) for i,p in enumerate(POKEMON) if p['name'].startswith(('バケッチャ (','パンプジン ('))])
emit_results['quoting']=emit('06_quoting_and_unicode.csv',[
   row(regular[0],400,explicit_name='試験,一'),
   row(regular[1],401,explicit_name='試験"二'),
   row(regular[2],402,explicit_name='試験三'),
])
report={'purpose':'STEP2_PUBLIC_IMPORTER_FIXTURES_NO_USER_DATA','csvHeader':HEADER,
        'masterSpecies':len(POKEMON),'subskills':len(SKILLS),'ingredientKinds':len(FOODS),
        'mewConcreteSkill':'Berry Burst','cases':emit_results,
        'candidateFromMasterOnly':True,'productionCsvAllowed':False}
(OUT/'FIXTURE_PLAN.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
