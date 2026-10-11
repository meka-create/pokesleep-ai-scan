#!/usr/bin/env python3
"""Read-only optional corroboration of species using observed helping seconds and carry.

Old OCR timing/ribbon structure is advisory only. Carry follows the
version 2.9.0 species-stage rule: it does NOT depend on the individual
Pokemon's catch/evolution history or skill level. All mismatches are REVIEW
flags, never candidate exclusion. No production CSV is generated.
"""
from __future__ import annotations
import json
import hashlib
import math
from collections import Counter
from pathlib import Path
from species_evidence_lab import evaluate

RIBBON_CARRY = (0, 1, 3, 6, 8)
RIBBON_HOURS = (0, 200, 500, 1000, 2000)
HELP_TOLERANCE_SEC = 1
ACTIVATION_LEVELS = (10, 25, 50, 70, 80)
# Snapshot is an old-format carryLimit master; a future live-value master must
# be audited before the v2.9.0 stage adjustment may be applied again.
PINNED_LEGACY_MASTER_SHA256 = 'd60410ba1f92d80c67ca3ff40bc8aa7a2cd51d4c03fc33f9e99fa83bb8e77a38'
# Frozen original species/metadata integrity anchor; verified against v18 baseline.
# This table is authored into trusted kit code by a human-reviewed release, NOT
# generated from any proposed new master. The old 249 are never auto-mutated.
LEGACY_BASE_NAMES = ('Bulbasaur', 'Ivysaur', 'Venusaur', 'Charmander', 'Charmeleon', 'Charizard', 'Squirtle', 'Wartortle', 'Blastoise', 'Caterpie', 'Metapod', 'Butterfree', 'Rattata', 'Raticate', 'Ekans', 'Arbok', 'Pikachu', 'Pikachu (Holiday)', 'Pikachu (Halloween)', 'Pikachu (Captain)', 'Raichu', 'Sandshrew', 'Sandslash', 'Clefairy', 'Clefable', 'Vulpix', 'Vulpix (Alola)', 'Ninetales', 'Ninetales (Alola)', 'Jigglypuff', 'Wigglytuff', 'Diglett', 'Dugtrio', 'Meowth', 'Persian', 'Psyduck', 'Golduck', 'Mankey', 'Primeape', 'Growlithe', 'Arcanine', 'Bellsprout', 'Weepinbell', 'Victreebel', 'Geodude', 'Graveler', 'Golem', 'Slowpoke', 'Slowbro', 'Magnemite', 'Magneton', "Farfetch'd", 'Doduo', 'Dodrio', 'Gastly', 'Haunter', 'Gengar', 'Onix', 'Cubone', 'Marowak', 'Chansey', 'Kangaskhan', 'Mr. Mime', 'Pinsir', 'Ditto', 'Eevee', 'Eevee (Halloween)', 'Eevee (Holiday)', 'Vaporeon', 'Jolteon', 'Flareon', 'Dratini', 'Dragonair', 'Dragonite', 'Mewtwo', 'Mew', 'Chikorita', 'Bayleef', 'Meganium', 'Cyndaquil', 'Quilava', 'Typhlosion', 'Totodile', 'Croconaw', 'Feraligatr', 'Pichu', 'Cleffa', 'Igglybuff', 'Togepi', 'Togetic', 'Natu', 'Xatu', 'Mareep', 'Flaaffy', 'Ampharos', 'Sudowoodo', 'Wooper', 'Wooper (Paldea)', 'Quagsire', 'Espeon', 'Umbreon', 'Murkrow', 'Slowking', 'Wobbuffet', 'Steelix', 'Shuckle', 'Heracross', 'Sneasel', 'Delibird', 'Houndour', 'Houndoom', 'Blissey', 'Raikou', 'Entei', 'Suicune', 'Larvitar', 'Pupitar', 'Tyranitar', 'Treecko', 'Grovyle', 'Sceptile', 'Torchic', 'Combusken', 'Blaziken', 'Mudkip', 'Marshtomp', 'Swampert', 'Ralts', 'Kirlia', 'Gardevoir', 'Slakoth', 'Vigoroth', 'Slaking', 'Sableye', 'Mawile', 'Aron', 'Lairon', 'Aggron', 'Plusle', 'Minun', 'Gulpin', 'Swalot', 'Trapinch', 'Vibrava', 'Flygon', 'Swablu', 'Altaria', 'Shuppet', 'Banette', 'Absol', 'Wynaut', 'Spheal', 'Spheal (Holiday)', 'Sealeo', 'Walrein', 'Bagon', 'Shelgon', 'Salamence', 'Latias', 'Latios', 'Turtwig', 'Grotle', 'Torterra', 'Chimchar', 'Monferno', 'Infernape', 'Piplup', 'Prinplup', 'Empoleon', 'Shinx', 'Luxio', 'Luxray', 'Drifloon', 'Drifblim', 'Honchkrow', 'Bonsly', 'Mime Jr.', 'Happiny', 'Spiritomb', 'Riolu', 'Lucario', 'Croagunk', 'Toxicroak', 'Snover', 'Abomasnow', 'Weavile', 'Magnezone', 'Togekiss', 'Leafeon', 'Glaceon', 'Gallade', 'Cresselia', 'Darkrai', 'Munna', 'Musharna', 'Dwebble', 'Crustle', 'Foongus', 'Amoonguss', 'Rufflet', 'Braviary', 'Tyrunt', 'Tyrantrum', 'Sylveon', 'Hawlucha', 'Dedenne', 'Pumpkaboo (Small)', 'Pumpkaboo (Medium)', 'Pumpkaboo (Large)', 'Pumpkaboo (Jumbo)', 'Gourgeist (Small)', 'Gourgeist (Medium)', 'Gourgeist (Large)', 'Gourgeist (Jumbo)', 'Noibat', 'Noivern', 'Grubbin', 'Charjabug', 'Vikavolt', 'Cutiefly', 'Ribombee', 'Stufful', 'Bewear', 'Comfey', 'Togedemaru', 'Mimikyu', 'Drampa', 'Cramorant', 'Toxel', 'Toxtricity (Amped)', 'Toxtricity (Low Key)', 'Sprigatito', 'Floragato', 'Meowscarada', 'Fuecoco', 'Crocalor', 'Skeledirge', 'Quaxly', 'Quaxwell', 'Quaquaval', 'Pawmi', 'Pawmo', 'Pawmot', 'Tinkatink', 'Tinkatuff', 'Tinkaton', 'Cetoddle', 'Cetitan', 'Clodsire')
LEGACY_BASE_SUBSKILL_EN = ('Berry Finding S', 'Dream Shard Bonus', 'Energy Recovery Bonus', 'Helping Bonus', 'Research EXP Bonus', 'Skill Level Up M', 'Sleep EXP Bonus', 'Helping Speed M', 'Ingredient Finder M', 'Inventory Up L', 'Inventory Up M', 'Skill Level Up S', 'Skill Trigger M', 'Helping Speed S', 'Ingredient Finder S', 'Inventory Up S', 'Skill Trigger S')
LEGACY_BASE_NATURE_EN = ('Bashful', 'Hardy', 'Docile', 'Quirky', 'Serious', 'Bold', 'Impish', 'Lax', 'Relaxed', 'Timid', 'Hasty', 'Jolly', 'Naive', 'Lonely', 'Adamant', 'Naughty', 'Brave', 'Calm', 'Gentle', 'Careful', 'Sassy', 'Modest', 'Mild', 'Rash', 'Quiet')
LEGACY_BASE_INGREDIENT_KEYS = ('apple', 'avocado', 'cacao', 'coffee', 'corn', 'egg', 'ginger', 'herb', 'honey', 'leek', 'milk', 'mushroom', 'oil', 'potato', 'pumpkin', 'sausage', 'soy', 'tail', 'tomato')
LEGACY_BASE_SPECIES_SHA256 = '0331d90286081ba07dc784918c0c959a4285aa59414151f3c2e7a6b3264f8a22'
LEGACY_BASE_NATURES_SHA256 = '963da12c7dd36e28852be41e0b38b0a2fb90078f7423e8dc4f4384a563a32206'
LEGACY_BASE_SUBSKILLS_SHA256 = '7b360066b86fd8ddcdef08f74d12f8d932728c16d6ff69927f95f29380a82c7a'
LEGACY_BASE_INGREDIENTS_SHA256 = '7ccc399b81cd69a1c53746dd34ff41a2c51e7b5b603d8407211c20a02248be57'
LEGACY_BASE_CUTOFF = '2026-10-05'
AUTO_PROMOTION_VERIFICATION = 'PINNED_SOURCE_AND_LIVE_PUBLIC_IMPORTER_CSV_ROUNDTRIP_PASS; PRODUCTION_CSV_HOLD'
# Generated only after real importer and pinned-source validation, by trusted publisher.
TRUSTED_PROMOTED_MASTER_SHA256 = None


def _canonical_sha(v):
    return hashlib.sha256(json.dumps(v, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def verify_additive_legacy_master(master, master_bytes, version=None, *, allow_release=False):
    """Independently anchor old gameplay data; reject mutations and ambiguity.

    New entries can be appended only after a real pinned-source/real-public
    importer proof in the trusted CI publisher. No old-species changes pass.
    Merely recomputing KIT_VERSION fingerprints cannot authorize promotion.
    """
    raw = hashlib.sha256(master_bytes).hexdigest()
    if raw == PINNED_LEGACY_MASTER_SHA256:
        if len(master.get('pokemon', [])) != 249:
            raise ValueError('Frozen baseline species count mismatch; HOLD')
        return {'policy': 'PINNED_V18_LEGACY', 'newSpecies': ()}
    if raw != TRUSTED_PROMOTED_MASTER_SHA256:
        raise ValueError('Promoted master not independently pinned by publisher; HOLD')
    if not isinstance(version, dict):
        raise ValueError('Unapproved promoted master (version missing); HOLD')
    if allow_release:
        # Only the separate release gate may invoke this branch. Retain the
        # exact independently pinned promoted-master SHA and legacy anchors.
        if (version.get('kitVersion') == '0.12.0-prototype' or
            version.get('productionCsvAllowed') is not True or
            version.get('compatibilityVerified') is not True or
            version.get('masterVerifiedAgainstLive') is not True):
            raise ValueError('Promoted master release eligibility incomplete; HOLD')
    else:
        # Scheduled auto-promotion and the development kit NEVER lift HOLD.
        if (version.get('kitVersion') != '0.12.0-prototype' or
            version.get('productionCsvAllowed') is not False or
            version.get('compatibilityVerified') is not False or
            version.get('masterVerifiedAgainstLive') is not False or
            'HOLD' not in version.get('status','')):
            raise ValueError('Unapproved promoted master HOLD policy; HOLD')
    if set(master) != {'cutoff','pokemon','ingredients','natures','subskills','provenance'}:
        raise ValueError('Unexpected master schema; HOLD')
    species = master['pokemon']
    if not isinstance(species,list) or not 249 < len(species) <= 2000:
        raise ValueError('Unreviewed species cardinality; HOLD')
    if any(not isinstance(p,dict) or not isinstance(p.get('name_en'),str) or
           not isinstance(p.get('name'),str) or not p['name'] for p in species):
        raise ValueError('Unreviewed species value; HOLD')
    en_names=[p['name_en'] for p in species]
    ja_names=[p['name'] for p in species]
    if len(set(en_names)) != len(en_names) or len(set(ja_names)) != len(ja_names):
        raise ValueError('Duplicate species identity; HOLD')
    existing=set(LEGACY_BASE_NAMES)
    if not existing.issubset(en_names):
        raise ValueError('Missing historical species; HOLD')
    by_en={p['name_en']:p for p in species}
    if _canonical_sha([by_en[n] for n in LEGACY_BASE_NAMES]) != LEGACY_BASE_SPECIES_SHA256:
        raise ValueError('Historical species gameplay values modified; HOLD')
    if not isinstance(master['ingredients'],dict) or not set(LEGACY_BASE_INGREDIENT_KEYS).issubset(master['ingredients']):
        raise ValueError('Historical ingredient keys changed; HOLD')
    if _canonical_sha({k:master['ingredients'][k] for k in LEGACY_BASE_INGREDIENT_KEYS}) != LEGACY_BASE_INGREDIENTS_SHA256:
        raise ValueError('Historical ingredient translations changed; HOLD')
    for key,basenames,basesha in (
      ('natures',LEGACY_BASE_NATURE_EN,LEGACY_BASE_NATURES_SHA256),
      ('subskills',LEGACY_BASE_SUBSKILL_EN,LEGACY_BASE_SUBSKILLS_SHA256)):
        items=master[key]
        if not isinstance(items,list) or any(not isinstance(s,dict) or not isinstance(s.get('en'),str) for s in items):
            raise ValueError('Invalid '+key+' structure; HOLD')
        mapping={s['en']:s for s in items}
        if len(mapping)!=len(items) or not set(basenames).issubset(mapping):
            raise ValueError('Historical '+key+' removed or duplicated; HOLD')
        if _canonical_sha([mapping[n] for n in basenames]) != basesha:
            raise ValueError('Historical '+key+' modified; HOLD')
        if key=='natures' and len(items)!=len(basenames):
            raise ValueError('Unknown nature added; HOLD')
        if key=='subskills' and len(items)!=len(basenames):
            # New subskill numeric meaning cannot be inferred from translations.
            raise ValueError('Unreviewed new subskill semantics; HOLD')
    additions=tuple(n for n in en_names if n not in existing)
    if not additions:raise ValueError('No new species; old master pin must remain; HOLD')
    for n in additions:
        p=by_en[n]
        required=('name_en','name','mainSkill','skill','frequency','carryLimit',
                  'evolutionCount','evolutionLeft','ing1','ing2','ing3')
        if any(k not in p for k in required):raise ValueError('New species incomplete; HOLD')
        if (type(p['frequency']) is not int or p['frequency']<=0 or
            type(p['carryLimit']) is not int or p['carryLimit']<0 or
            type(p['evolutionCount']) is not int or p['evolutionCount']<0):
            raise ValueError('New species numeric shape invalid; HOLD')
        if not p['mainSkill'] or not p['skill']:
            raise ValueError('New species skill missing; HOLD')
        for key in ('ing1','ing2','ing3'):
            d=p[key]
            if d is not None and (not isinstance(d,dict) or
              d.get('key') not in master['ingredients'] or
              d.get('name') != master['ingredients'][d['key']]):
                raise ValueError('New species ingredient value invalid; HOLD')
    provenance=master['provenance']
    commit=version.get('sourceCommit')
    if (not isinstance(commit,str) or len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit) or
       not isinstance(provenance,dict) or provenance.get('sourceCommit')!=commit or
       provenance.get('verification') != AUTO_PROMOTION_VERIFICATION or
       not isinstance(provenance.get('importerProofSha256'),str) or
       len(provenance['importerProofSha256'])!=64 or
       any(c not in '0123456789abcdef' for c in provenance['importerProofSha256'])):
        raise ValueError('Missing independently validated import proof marker; HOLD')
    if version.get('rawAssetSha256',{}).get('MASTER_DATA.json') != raw:
        raise ValueError('Promoted master raw digest mismatch; HOLD')
    return {'policy':'ADDITIONS_ONLY_WITH_PINNED_LEGACY', 'newSpecies':additions}

NEUTRAL = {'speed': 1.0, 'energy': 1.0, 'ing': 1.0, 'skill': 1.0}


def actual_ribbon_tier(sleep_hours):
    """Only call with an actually observed sleep-hour count, not CSV default."""
    if sleep_hours is None:
        return None
    if type(sleep_hours) not in (int, float) or not math.isfinite(sleep_hours) or sleep_hours < 0:
        raise ValueError('Observed hours must be nonnegative finite number or null')
    return max(i for i, cutoff in enumerate(RIBBON_HOURS) if sleep_hours >= cutoff)


def verified_optional_number(value, name, integer=True):
    if value is None:
        return None
    if (type(value) is not int) if integer else (type(value) not in (float,int)):
        raise ValueError(f'{name} must be a number or null, not a coercible string')
    if value < 0 or not math.isfinite(value):
        raise ValueError(f'{name}: must be finite and nonnegative')
    return value


def active_modifiers(master, subskills, level):
    needed=sum(level>=t for t in ACTIVATION_LEVELS)
    # None is unread, not 'no subskill'. For a numeric comparison the
    # activated subskills must all have been read; the locked ones may be null.
    if not isinstance(subskills,list) or len(subskills)!=5 or any(not x for x in subskills[:needed]):
        return None
    d={x['ja']:x for x in master['subskills']}
    mod={k:0 for k in ('hs','inv','sl')}
    for name in subskills[:needed]:
        if name not in d:
            return None
        for k in mod:
            mod[k]+=d[name].get(k,0)
    return mod


def ribbon_speed(sp,tier):
    el=sp.get('evolutionLeft',0)
    if el == 0: return 1
    if tier>=4: return .75 if el==2 else .88
    if tier>=2: return .89 if el==2 else .95
    return 1


def old_help_seconds(sp,level,nature_speed,help_subskills,ribbon):
    # Equivalent to the publicly published old classifier's time factor,
    # with its special Lv10 edge and JS truncation. Advisory only.
    if level<1 or level>70: return None  # Stay within independently tested level range.
    factor=((501-level)/500)*nature_speed*ribbon_speed(sp,ribbon)*(1-help_subskills*.07)
    factor=math.floor(float(f'{factor*10000:.6f}'))/10000
    odd=.1 if level==10 and sp['frequency']==2600 else 0
    return math.floor(sp['frequency']*factor-odd+1e-9)


def current_species_carry_baseline(p):
    """Derive current carry from this PINNED, legacy-shaped master record.

    The master field carryLimit is pre-v2.9.0 species inventory. Official
    v2.9.0 applies the historical +5 per species evolution STAGE to all
    members of that species, including directly caught evolved Pokemon.
    Here evolutionCount is the SPECIES stage, not actual player evolutions.
    Negative stage is treated as no standard evolution for this advisory
    report. Never use this estimate for hard species exclusion.
    """
    base=p.get('carryLimit')
    stage=p.get('evolutionCount')
    if type(base) is not int or base<0 or type(stage) is not int:
        raise ValueError('Master carryLimit/evolutionCount invalid')
    species_stage=max(0,stage)
    return base + 5*species_stage


def observed_numeric(candidate,master,rec):
    """Return reports; none of this may drive exclusion/autocorrection."""
    level=rec.get('level')
    if type(level) is not int or not 1<=level<=70:
        return {'status':'INSUFFICIENT_LEVEL', 'canCorroborate':False}
    nat={x['ja']:x for x in master['natures']}.get(rec.get('nature'))
    mod=active_modifiers(master,rec.get('subskills'),level)
    if nat is None or mod is None:
        return {'status':'INSUFFICIENT_NATURE_OR_SUBSKILLS','canCorroborate':False}
    helpval=verified_optional_number(rec.get('helpSeconds'), 'helpSeconds')
    carryval=verified_optional_number(rec.get('carry'), 'carry')
    spval=verified_optional_number(rec.get('sp'), 'sp')
    sleep=verified_optional_number(rec.get('sleepTogetherHoursObserved'), 'sleepTogetherHoursObserved',False)
    mint=rec.get('whiteMintMarkObserved')
    if mint not in (None,True,False):
        raise ValueError('whiteMintMarkObserved must be boolean or null')
    if helpval is None and carryval is None and spval is None:
        return {'status':'NO_NUMERIC_VALUES','canCorroborate':False}
    p=next(x for x in master['pokemon'] if x['name']==candidate)
    if p['name_en'] not in LEGACY_BASE_NAMES:
        return {'status':'NEW_SPECIES_NUMERIC_HOLD', 'canCorroborate':False,
                'reason':'New species numeric model not independently approved',
                'noCandidateRemoval':True, 'noAutoSelection':True}
    tiers=range(5) if sleep is None else (actual_ribbon_tier(sleep),)
    natures=(('normal',nat),('neutralized',NEUTRAL)) if mint is None else ((('neutralized',NEUTRAL),) if mint else (('normal',nat),))
    # IMPORTANT: maximum carry is independent of capture route after v2.9.0.
    # Species evolution STAGE is a master attribute; player evolution HISTORY
    # and observed skillLevel are irrelevant to helping-time/carry matching.
    baseline=current_species_carry_baseline(p)
    species_stage=max(0,p['evolutionCount'])
    possibilities=[]
    for tier in tiers:
        for mode,nature in natures:
            help_time=old_help_seconds(p,level,nature['speed'],mod['hs'],tier)
            carry=baseline+RIBBON_CARRY[tier]+mod['inv']*6
            possibilities.append({'ribbonTier':tier,'mintEffect':mode,
                 'calculatedHelpSeconds':help_time,'calculatedCarry':carry,
                 'helpMatches':None if helpval is None else abs(help_time-helpval)<=HELP_TOLERANCE_SEC,
                 'carryMatches':None if carryval is None else carry==carryval})
    any_help = None if helpval is None else any(x['helpMatches'] for x in possibilities)
    any_carry = None if carryval is None else any(x['carryMatches'] for x in possibilities)
    joint = None if helpval is None or carryval is None else any(x['helpMatches'] and x['carryMatches'] for x in possibilities)
    supports=[x for x in possibilities if (helpval is None or x['helpMatches']) and (carryval is None or x['carryMatches'])]
    # SP is deliberately NOT compared or used as an exclusion filter.
    return {'status':'ADVISORY_ONLY','canCorroborate':True,'helpSupported':any_help,
      'carrySupported':any_carry,'jointHelpCarrySupported':joint,
      'observedSpRecordedNotCompared':spval, 'ribbonTiersConsidered':list(tiers),
      'currentSpeciesCarryBaselineEstimate':baseline, 'legacyMasterCarryLimit':p['carryLimit'],
      'speciesEvolutionStageBonusAppliedUniversally':species_stage*5,
      'carryIndependentOfActualEvolutionHistory':True,
      'skillLevelNotUsedForCarryOrHelpingTime':True,
      'carryBaselineProvenance':'PINNED_MASTER_LEGACY_BASE_PLUS_V2_9_SPECIES_STAGE_BONUS_ADVISORY',
      'natureModesConsidered':[t[0] for t in natures],
      'matchingStateCount':len(supports), 'matchingStates':supports[:4],
      'noCandidateRemoval':True, 'noAutoSelection':True}


def evaluate_observation(master,rec):
    base=evaluate(master,{'species':rec.get('species'),'foods':rec.get('foods',[None]*3),
                          'mainSkill':rec.get('mainSkill'),'quantities':rec.get('quantities')})
    numerics={s:observed_numeric(s,master,rec) for s in base['candidates']}
    h={s for s,v in numerics.items() if v.get('jointHelpCarrySupported') is True}
    base['numericCandidateReports']=numerics
    base['numericSupportedCandidates']=sorted(h)
    base['numericEvidencePolicy']='READ_ONLY_NO_EXCLUSION_NO_AUTOCORRECT_NO_SP_STRICT'
    base['csvSleepTogetherHours']=rec.get('csvSleepTogetherHours')
    base['sleepTogetherHoursObserved']=rec.get('sleepTogetherHoursObserved')
    base['sleepHoursDefaultNeverUsedForRibbon']=True
    base['shinyObserved']=rec.get('shinyObserved')
    base['shinyPolicy']='IMAGE_VISIBLE_IF_CLEAR_ELSE_CSV_DEFAULT_ZERO'
    base['imageId']=rec.get('imageId')
    base['referenceIdentityVerification']=rec.get('referenceIdentityVerification')
    return base


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--observations',type=Path,required=True)
    parser.add_argument('--master',type=Path,default=Path(__file__).with_name('MASTER_DATA.json'))
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args()
    master_bytes=a.master.read_bytes()
    master=json.loads(master_bytes.decode('utf-8'))
    version_path=a.master.with_name('KIT_VERSION.json')
    version=json.loads(version_path.read_text(encoding='utf-8')) if version_path.exists() else None
    verify_additive_legacy_master(master,master_bytes,version)
    obs=json.loads(a.observations.read_text(encoding='utf-8'))
    if obs.get('purpose')!='READ_ONLY_AUDIT_NOT_GOLD': raise ValueError('untrusted purpose or observations')
    results=[evaluate_observation(master,x) for x in obs['imageObservations']]
    summary=dict(Counter(x['status'] for x in results))
    out={'status':'PROTOTYPE_HOLD','noProductionCsv':True,'count':len(results),'summary':summary,
         'observationsSource':obs.get('sourceDescription'),'results':results}
    a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('READ_ONLY',len(results),summary)
    for r in results:
        total=len(r['candidates']); joint=len(r['numericSupportedCandidates']);
        print(r['imageId'],r['reportedSpecies'],f'food-skill={total}',f'jointNumericSupport={joint}',
              'reportedSupported='+str(r.get('reportedSpecies') in r['numericSupportedCandidates']))

if __name__=='__main__':main()
