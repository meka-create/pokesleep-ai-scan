"""Release v25 regressions: synthetic PNG only; no private corpus or Golden data."""
import hashlib,json,pathlib,shutil,struct,subprocess,sys,tempfile,unittest,zlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
KIT=ROOT/'release-kit-assets'

def png():
    def c(k,v):return struct.pack('>I',len(v))+k+v+struct.pack('>I',zlib.crc32(k+v)&0xffffffff)
    raw=b''.join(b'\x00'+b'\x7f\x7f\x7f'*64 for _ in range(64))
    return b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',64,64,8,2,0,0,0))+c(b'IDAT',zlib.compress(raw))+c(b'IEND',b'')

class FinalFourFixes(unittest.TestCase):
    def test_f01_upstream_audit_only_no_privileged_publisher(self):
        source=(ROOT/'.github/workflows/verified-master-autopromotion.yml').read_text()
        watcher=(ROOT/'.github/workflows/ai-scan-readonly-upstream-watch.yml').read_text()
        assert 'READ ONLY' in source and '\n  publish:' not in source and 'contents: write' not in source
        assert 'schedule:' in source and 'git add -- update-status.json' in watcher
    def test_f04_dev_public_check_is_labeled_not_release(self):
        content=(ROOT/'.github/workflows/verify-published-kit.yml').read_text()
        assert 'DEV kit HOLD integrity' in content and 'NOT_A_RELEASE_AUDIT' in content
        assert 'release-kit-assets/' in (ROOT/'.github/workflows/release-public-http-audit.yml').read_text()
    def test_f02_f03_real_process_without_and_with_approval(self):
        with tempfile.TemporaryDirectory() as td:
            tmp=pathlib.Path(td);pkg=tmp/'kit';shutil.copytree(KIT,pkg)
            (pkg/'images').mkdir()
            b=png(); (pkg/'images/IMG-0001.png').write_bytes(b)
            v=json.loads((pkg/'KIT_VERSION.json').read_text())
            master=json.loads((pkg/'MASTER_DATA.json').read_text())
            p=next(p for p in master['pokemon'] if p['name']=='フシギダネ')
            subs=[s['ja'] for s in master['subskills'][:5]]
            r={'schemaVersion':'ai-reading-v0.1','kitVersion':v['kitVersion'],
               'decisions':[{'imageId':'IMG-0001','decision':'include','unresolved':[],
                 'reviewComplete':True,'data':{'nickname':'合成','species':'フシギダネ',
                 'level':30,'skillLevel':1,'foods':[p['ing1']['name']]*3,
                 'mainSkill':p['mainSkill'],'nature':'すなお','subskills':subs}}]}
            manifest={'schemaVersion':'ai-input-manifest-v0.1','kitVersion':v['kitVersion'],
             'inputImageCount':1,'sourceSelectedCount':1,'duplicatePolicy':'user-selected-keep-all',
             'images':[{'id':'IMG-0001','path':'images/IMG-0001.png',
             'originalFilename':'synthetic.png','size':len(b),
             'sha256':hashlib.sha256(b).hexdigest()}]}
            (pkg/'INPUT_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False))
            rec=tmp/'records.json';rec.write_text(json.dumps(r,ensure_ascii=False))
            obs=tmp/'obs.json';obs.write_text(json.dumps({'purpose':'READ_ONLY_AUDIT_NOT_GOLD','imageObservations':[{'imageId':'IMG-0001','speciesVisualConfirmed':True}]},ensure_ascii=False))
            def run(name,*args):
                return subprocess.run([sys.executable,str(pkg/name),*map(str,args)],capture_output=True,text=True,timeout=25)
            (pkg/'pokesleep_import.csv').write_text('STALE')
            direct=run('VALIDATOR.py','--package-dir',pkg,'--records',rec)
            assert direct.returncode!=0 and 'RELEASE_EXPORT_GATE.py' in direct.stderr
            assert not (pkg/'pokesleep_import.csv').exists()
            output=tmp/'report.json'
            default=run('SPECIES_AUDIT.py','--package-dir',pkg,'--records',rec,'--observations',obs,'--output',output)
            assert default.returncode!=0 and not output.exists()
            approved=run('SPECIES_AUDIT.py','--release-audit','--package-dir',pkg,
                         '--records',rec,'--observations',obs,'--output',output)
            assert approved.returncode==0,approved.stderr
            assert json.loads(output.read_text())['total']==1
            assert not (pkg/'pokesleep_import.csv').exists() and not (pkg/'RELEASE_GATE_STATUS.json').exists()
            (pkg/'SPECIES_AUDIT.py').write_text((pkg/'SPECIES_AUDIT.py').read_text()+'\n# tamper\n')
            output.unlink()
            bad=run('SPECIES_AUDIT.py','--release-audit','--package-dir',pkg,
                    '--records',rec,'--observations',obs,'--output',output)
            assert bad.returncode!=0 and not output.exists()

if __name__=='__main__':unittest.main()
