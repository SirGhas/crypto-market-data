import unittest
from unittest.mock import patch
from engine.alpha_holdout_v209 import evaluate, summarize

class HoldoutTests(unittest.TestCase):
    def test_empty_group(self):
        self.assertIsNone(summarize([])["HIGH"]["rejection_fraction"])
    @patch("engine.alpha_holdout_v209.replay")
    def test_chronological_boundary(self, replay):
        bars = [(i*14400,) for i in range(100)]
        replay.return_value = {"events":[{"decision_epoch":i*14400,"score_band":"HIGH","outcome":"CONFIRMED_REJECTION"} for i in (50,65,70)]}
        result = evaluate(bars)
        self.assertEqual(result["earlier"]["HIGH"]["observations"],1)
        self.assertEqual(result["holdout"]["HIGH"]["observations"],1)
        self.assertEqual(result["excluded_cross_boundary"],1)
        self.assertFalse(result["trading_enabled"])
