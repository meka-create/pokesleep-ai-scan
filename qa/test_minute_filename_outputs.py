"""Minute-only output names. Run release-kit import in a subprocess to avoid
polluting the legacy dev-kit RELEASE_EXPORT_GATE module cache in unittest discover.
"""
import pathlib, subprocess, sys, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
KIT=ROOT/'release-kit-assets'

class TimestampedOutputTests(unittest.TestCase):
    def test_minute_and_collisions_without_overwrite(self):
        script=r"""
from RELEASE_EXPORT_GATE import timestamped_csv_name,JST
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
with TemporaryDirectory() as folder:
    at=datetime(2026,10,11,15,38,59,987654,tzinfo=JST)
    first=timestamped_csv_name(folder,now=at)
    assert first=='pokesleep_import_20261011_1538.csv',first
    (Path(folder)/first).write_text('prior export')
    assert timestamped_csv_name(folder,now=at)=='pokesleep_import_20261011_1538_2.csv'
    (Path(folder)/'pokesleep_import_20261011_1538_2.csv').write_text('prior second export')
    assert timestamped_csv_name(folder,now=at)=='pokesleep_import_20261011_1538_3.csv'
    assert timestamped_csv_name(folder,now=datetime(2026,10,11,6,39,59,tzinfo=timezone.utc))=='pokesleep_import_20261011_1539.csv'
"""
        result=subprocess.run([sys.executable,'-c',script],cwd=str(KIT),
                              capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    def test_zip_minute_only_with_collision_counter(self):
        app=(ROOT/'app.js').read_text(encoding='utf-8')
        self.assertIn('function nextZipFilename(imageCount)',app)
        self.assertIn('zipNameCounts.set(stem,number)',app)
        self.assertIn('pad(date.getHours())+pad(date.getMinutes())',app)
        self.assertNotIn('getSeconds()',app)
        self.assertNotIn('getMilliseconds()',app)

if __name__=='__main__':
    unittest.main()
