import unittest
from datetime import datetime, timedelta, timezone
from paper_performance import evaluate_paper_event

T = datetime(2026, 11, 17, 15, tzinfo=timezone.utc)
EVENT = {"event_id": "example", "asset": "BTC", "mode": "PAPER_ONLY",
         "execution_allowed": False, "decision": "BUY_PAPER",
         "observed_at_utc": T.isoformat(), "reference_price": "100"}

class PerformanceTests(unittest.TestCase):
    def test_long_profit_after_fee(self):
        r = evaluate_paper_event(EVENT, "102", T+timedelta(hours=1))
        self.assertEqual(r["net_return_pct"], "1.900")
        self.assertEqual(r["outcome"], "WIN")

    def test_short_profit_after_fee(self):
        r = evaluate_paper_event({**EVENT, "decision": "SELL_PAPER"}, "98", T+timedelta(hours=1))
        self.assertEqual(r["outcome"], "WIN")

    def test_mark_before_signal_rejected(self):
        with self.assertRaisesRegex(ValueError, "MARK_MUST_FOLLOW_SIGNAL"):
            evaluate_paper_event(EVENT, "102", T)

    def test_nonfinite_mark_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_PAPER_MARK"):
            evaluate_paper_event(EVENT, "NaN", T+timedelta(hours=1))

    def test_live_execution_rejected(self):
        with self.assertRaisesRegex(ValueError, "NOT_PAPER_EVENT"):
            evaluate_paper_event({**EVENT, "execution_allowed": True}, "102", T+timedelta(hours=1))

    def test_watch_not_evaluated_as_trade(self):
        with self.assertRaisesRegex(ValueError, "NOT_DIRECTIONAL_PAPER_SIGNAL"):
            evaluate_paper_event({**EVENT, "decision": "WATCH"}, "102", T+timedelta(hours=1))

if __name__ == "__main__":
    unittest.main()
