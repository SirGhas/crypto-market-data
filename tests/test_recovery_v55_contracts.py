"""RECOVERY-003: combined score/guard/report contract and UI safety checks."""
import json
import re
import unittest
from pathlib import Path
from dual_screen_v53 import COINS, WEIGHTS
from unified_guard_v548 import band

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
class RecoveryContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dual=json.loads((DATA/"dual_screen_v53.json").read_text())
        cls.guard=json.loads((DATA/"unified_guard_v548.json").read_text())
        cls.health=json.loads((DATA/"delivery_health_v550.json").read_text())
        cls.ui=(ROOT/"dashboard"/"index.html").read_text()

    def test_report_schema_and_coverage(self):
        self.assertEqual(self.dual["weights"],WEIGHTS)
        self.assertEqual(set(x["coin"] for x in self.dual["evaluations"]),set(COINS))
        self.assertEqual(set(self.guard["coins"]),set(COINS))
        self.assertEqual(len(self.dual["evaluations"]),self.dual["summary"]["scanned"])

    def test_component_score_integrity(self):
        for e in self.dual["evaluations"]:
            if e["score"] is None:
                self.assertEqual(e["tier"],"blocked")
                continue
            self.assertEqual(e["score"],sum(e["score_components"].values()),e["coin"])
            for k,v in e["score_components"].items():
                self.assertIn(k,WEIGHTS)
                self.assertLessEqual(v,WEIGHTS[k])
                self.assertGreaterEqual(v,0)

    def test_guard_matches_report_snapshot(self):
        for e in self.dual["evaluations"]:
            g=self.guard["coins"][e["coin"]]
            self.assertEqual(g["score"],e["score"])
            self.assertEqual(g["color_band"],band(e["score"]))
            self.assertEqual(g["original_tier"],e["tier"])
            if e["tier"]=="blocked":
                self.assertEqual(g["positive_publication_gate"],"BLOCK")

    def test_no_orders_or_false_delivery(self):
        self.assertIn("no_orders",self.dual["mode"])
        self.assertIn("no_orders",self.guard["mode"])
        self.assertIn("outbox",self.health)
        self.assertNotIn("trade_authorized",self.dual)

    def test_ui_is_read_only_and_staleness_aware(self):
        for token in ['lang="fa"','dir="rtl"','Asia/Tehran',
                      'dual_screen_v53.json','unified_guard_v548.json',
                      'delivery_health_v550.json','replaceChildren',
                      'textContent','90*60*1000']:
            self.assertIn(token,self.ui)
        self.assertNotIn("fetch(\"https://",self.ui)
        self.assertNotIn("innerHTML",self.ui)
        self.assertNotIn("sendOrder(",self.ui)

if __name__=="__main__":
    unittest.main()
