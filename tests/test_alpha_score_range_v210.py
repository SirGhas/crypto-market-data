import unittest
from engine.alpha_score_range_v210 import attainable,summarize

class ScoreRangeTests(unittest.TestCase):
    def test_4h_ceiling(self):
        self.assertEqual(max(attainable()["4h"]),59)
    def test_daily_high_reachable(self):
        self.assertGreaterEqual(min(attainable()["1D"]),60)
    def test_duplicate_window_count(self):
        e={"heuristic_score":42,"outcome":"NO_TOUCH","decision_epoch":1}
        result=summarize([e,e])
        self.assertEqual(result["42"]["decision_windows"],1)
        self.assertEqual(result["42"]["outcomes"]["NO_TOUCH"],2)
