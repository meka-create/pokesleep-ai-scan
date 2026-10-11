"""Minute-only filename convention: never overwrite prior verified CSVs."""
import importlib.util, json, pathlib, tempfile, unittest
from datetime import datetime, timedelta, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]
FILE=ROOT/'release-kit-assets/RELEASE_EXPORT_GATE.py'
# Import from the legitimate kit directory (relative companion modules).
import sys
sys.path.insert(0,str(FILE.parent))
from RELEASE_EXPORT_GATE import timestamped_csv_name, JST

class TimestampedOutputTests(unittest.TestCase):
    def test_minute_only_and_suffix_on_collision(self):
        with tempfile.TemporaryDirectory() as folder:
            at=datetime(2026,10,11,15,38,59,987654,tzinfo=JST)
            first=timestamped_csv_name(folder,now=at)
            self.assertEqual(first,'pokesleep_import_20261011_1538.csv')
            (pathlib.Path(folder)/first).write_text('already generated')
            self.assertEqual(timestamped_csv_name(folder,now=at),'pokesleep_import_20261011_1538_2.csv')
            (pathlib.Path(folder)/'pokesleep_import_20261011_1538_2.csv').write_text('old second')
            self.assertEqual(timestamped_csv_name(folder,now=at),'pokesleep_import_20261011_1538_3.csv')
    def test_csv_time_uses_japan_time(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(timestamped_csv_name(folder,now=datetime(2026,10,11,6,38,59,tzinfo=timezone.utc)),
                             'pokesleep_import_20261011_1538.csv')
    def test_web_zip_name_is_minute_only(self):
        app=(ROOT/'app.js').read_text(encoding='utf-8')
        self.assertIn("function nextZipFilename(imageCount)",app)
        self.assertIn("zipNameCounts.set(stem,number)",app)
        self.assertIn("pad(date.getHours())+pad(date.getMinutes())",app)
        self.assertNotIn('getSeconds()',app)
        self.assertNotIn('getMilliseconds()',app)

if __name__=='__main__':
    unittest.main()
