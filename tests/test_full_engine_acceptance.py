import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from full_engine_acceptance import REQUIRED, assess, write_report

NOW=datetime(2026,10,18,tzinfo=timezone.utc)
def valid():
    return {name:{"status":"PASS","as_of_utc":NOW.isoformat(),"evidence":"fixture"} for name in REQUIRED}

class FullEngineAcceptanceTests(unittest.TestCase):
    def test_missing_components_fail_closed(self):
        r=assess({},NOW)
        self.assertEqual(r["verdict"],"FAIL")
        self.assertEqual(len(r["failed_components"]),len(REQUIRED))

    def test_all_components_required(self):
        r=assess(valid(),NOW)
        self.assertEqual(r["verdict"],"PASS")
        self.assertEqual(r["passed"],len(REQUIRED))

    def test_future_macro_fails(self):
        v=valid()
        v["macro"]["as_of_utc"]=(NOW+timedelta(seconds=1)).isoformat()
        r=assess(v,NOW)
        self.assertEqual(r["verdict"],"FAIL")
        self.assertIn("macro",r["failed_components"])

    def test_evidence_required(self):
        v=valid()
        del v["geopolitics_news"]["evidence"]
        self.assertIn("geopolitics_news",assess(v,NOW)["failed_components"])

    def test_render_html_and_json(self):
        with tempfile.TemporaryDirectory() as folder:
            write_report(assess({},NOW),folder)
            self.assertIn("dir=\"rtl\"",Path(folder,"full_engine_acceptance.html").read_text())
            self.assertTrue(Path(folder,"full_engine_acceptance.json").exists())

if __name__=="__main__":
    unittest.main()
