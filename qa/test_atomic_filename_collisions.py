"""Atomic exclusive CSV publishing: concurrent same-minute attempts never replace data."""
import pathlib, subprocess, sys, tempfile, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
KIT=ROOT/'release-kit-assets'

class AtomicTimestampedCSVTests(unittest.TestCase):
    def test_two_processes_same_minute_distinct_names_and_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            source=r"""
import pathlib,sys
from datetime import datetime
from RELEASE_EXPORT_GATE import write_unique_csv,JST
folder=pathlib.Path(sys.argv[1])
payload=sys.argv[2].encode('utf-8')
name=write_unique_csv(folder,payload,now=datetime(2026,10,11,15,38,1,tzinfo=JST))
print(name,flush=True)
"""
            writers=[
                subprocess.Popen([sys.executable,'-c',source,folder,word],
                    cwd=str(KIT),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                for word in ('left-process','right-process')
            ]
            filenames=[]
            for proc in writers:
                out,err=proc.communicate(timeout=30)
                self.assertEqual(proc.returncode,0,err)
                filenames.append(out.strip())
            self.assertEqual(len(set(filenames)),2,filenames)
            self.assertEqual(set(filenames),{
                'pokesleep_import_20261011_1538.csv',
                'pokesleep_import_20261011_1538_2.csv'
            })
            saved={(pathlib.Path(folder)/n).read_text() for n in filenames}
            self.assertEqual(saved,{'left-process','right-process'})
            self.assertEqual(len(list(pathlib.Path(folder).glob('*.tmp'))),0)

    def test_rejects_overwrite_and_retains_existing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            source=r"""
from RELEASE_EXPORT_GATE import write_unique_csv,JST
from datetime import datetime
from pathlib import Path
import sys
folder=Path(sys.argv[1]);dt=datetime(2026,10,11,15,38,0,tzinfo=JST)
original=folder/'pokesleep_import_20261011_1538.csv'
original.write_bytes(b'ORIGINAL')
name=write_unique_csv(folder,b'NEW',now=dt)
assert name=='pokesleep_import_20261011_1538_2.csv'
assert original.read_bytes()==b'ORIGINAL'
assert (folder/name).read_bytes()==b'NEW'
"""
            r=subprocess.run([sys.executable,'-c',source,folder],
                cwd=str(KIT),capture_output=True,text=True,timeout=30)
            self.assertEqual(r.returncode,0,r.stderr)

if __name__=='__main__':
    unittest.main()
