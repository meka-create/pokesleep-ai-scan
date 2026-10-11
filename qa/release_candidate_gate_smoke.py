#!/usr/bin/env python3
"""Real release integrated-gate synthetic smoke and negative safety checks.

Runs only on an isolated candidate checkout; no app deployment and no genuine
user screenshot interpretation is claimed.
"""
from __future__ import annotations
import pathlib, tempfile, shutil, json, hashlib, sys, csv, io
from copy import deepcopy
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'release-kit-assets'))
from RELEASE_EXPORT_GATE import run,release_preflight,CSV_NAME,BINDING_NAME,STATUS_NAME
K=ROOT/'release-kit-assets'
sha=lambda b:hashlib.sha256(b).hexdigest()

with tempfile.TemporaryDirectory(prefix='release_gate_candidate_') as td:
    folder=pathlib.Path(td);pkg=folder/'package';shutil.copytree(K,pkg)
    (pkg/'images').mkdir()
    # A byte-valid synthetic PNG avoids relying on optional test-site example metadata.
    import struct,zlib
    def png_chunk(kind,payload):
        return (struct.pack('>I',len(payload))+kind+payload+
                struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff))
    raw=b''.join(b'\x00'+b'\x7f\x7f\x7f'*64 for _ in range(64))
    data=(b'\x89PNG\r\n\x1a\n'+png_chunk(b'IHDR',struct.pack('>IIBBBBB',64,64,8,2,0,0,0))+
          png_chunk(b'IDAT',zlib.compress(raw))+png_chunk(b'IEND',b''))
    (pkg/'images/IMG-0001.png').write_bytes(data)
    v=json.loads((pkg/'KIT_VERSION.json').read_text(encoding='utf-8'))
    manifest={'schemaVersion':'ai-input-manifest-v0.1',
       'kitVersion':v['kitVersion'],'inputImageCount':1,'sourceSelectedCount':1,
       'duplicatePolicy':'user-selected-keep-all',
       'images':[{'id':'IMG-0001','path':'images/IMG-0001.png',
                  'originalFilename':'synthetic-test.png','size':len(data),'sha256':sha(data)}]}
    (pkg/'INPUT_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False),encoding='utf-8')
    master=json.loads((pkg/'MASTER_DATA.json').read_text(encoding='utf-8'))
    poke=next(p for p in master['pokemon'] if p['name']=='フシギダネ')
    s=[x['ja'] for x in master['subskills'][:5]]
    d={'nickname':'検証,用"CSV','species':poke['name'],'level':30,'skillLevel':1,
       'foods':[poke['ing1']['name']]*3,
       'mainSkill':poke['mainSkill'],'nature':'すなお','subskills':s,
       'sleepTogetherHours':0,'shiny':0,
       'fieldEvidence':{'sleepTogetherHours':'user-policy-default','shiny':'user-policy-default'}}
    records={'schemaVersion':'ai-reading-v0.1','kitVersion':v['kitVersion'],
        'decisions':[{'imageId':'IMG-0001','decision':'include','unresolved':[],
                      'reviewComplete':True,'data':d}]}
    recordsfile=folder/'records.json'
    recordsfile.write_text(json.dumps(records,ensure_ascii=False),encoding='utf-8')
    observations={'purpose':'READ_ONLY_AUDIT_NOT_GOLD','imageObservations':[
        {'imageId':'IMG-0001','speciesVisualConfirmed':True}]}
    obsfile=folder/'observations.json'
    obsfile.write_text(json.dumps(observations,ensure_ascii=False),encoding='utf-8')
    out=folder/'output'
    result=run(pkg,recordsfile,obsfile,out,explicit_release=True)
    assert result['status']=='PASS',result
    assert result['included']==1 and result['excluded']==0
    csv_data=(out/CSV_NAME).read_bytes()
    rows=list(csv.reader(io.StringIO(csv_data.decode('utf-8'),newline=''),strict=True))
    assert len(rows)==2 and len(rows[0])==16
    assert rows[1][0]=='検証,用"CSV' and rows[1][1]=='フシギダネ'
    binding=json.loads((out/BINDING_NAME).read_text())
    status=json.loads((out/STATUS_NAME).read_text())
    assert binding['csvSHA256']==status['csvSHA256']==sha(csv_data)
    assert binding['rows'][0]['imageId']=='IMG-0001'
    print('PASS: release gate accepted synthetic record, row binding & digest',flush=True)
    # Re-run without explicit release flag must delete prior 3-file output.
    try:run(pkg,recordsfile,obsfile,out,explicit_release=False)
    except ValueError as e:assert 'HOLD' in str(e)
    else:raise AssertionError('release flag not enforced')
    assert not any((out/n).exists() for n in (CSV_NAME,BINDING_NAME,STATUS_NAME))
    print('PASS: deny without release flag, previous artifacts erased',flush=True)
    # Tampering evidence must be rejected before any CSV can appear.
    evidence=pkg/'RELEASE_EVIDENCE.json'
    doc=json.loads(evidence.read_text());doc['explicitUserApproval']=False
    evidence.write_text(json.dumps(doc,ensure_ascii=False),encoding='utf-8')
    try:run(pkg,recordsfile,obsfile,out,explicit_release=True)
    except ValueError:pass
    else:raise AssertionError('tampered release evidence accepted')
    assert not (out/CSV_NAME).exists()
    print('PASS: deny tampered release evidence, no output',flush=True)
