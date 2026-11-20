import unittest
from datetime import datetime, timedelta, timezone
from paper_signal_gate import evaluate

NOW = datetime(2026, 11, 17, 15, 30, tzinfo=timezone.utc)

class PaperGateTests(unittest.TestCase):
    def test_unapproved_feed_stays_blocked(self):
        result = evaluate({"status": "PRICE_SCALE_VERIFIED", "frames": {
            "15m": {"last_closed_at_utc": NOW.isoformat()}}}, NOW)
        self.assertEqual(result["signal"], "NO_SIGNAL")
        self.assertFalse(result["execution_allowed"])
        self.assertIn("REFERENCE_PARITY_PENDING", result["reasons"])

    def test_stale_feed_stays_blocked(self):
        feed = {"status": "OK", "analysis_enabled": True,
                "reference_parity_approved": True, "liquidity_approved": True,
                "frames": {"15m": {"last_closed_at_utc": (NOW-timedelta(hours=2)).isoformat()}}}
        self.assertIn("STALE_OR_FUTURE_CANDLE", evaluate(feed, NOW)["reasons"])

    def test_fresh_approved_feed_eligible_only_for_paper(self):
        feed = {"status": "OK", "analysis_enabled": True,
                "reference_parity_approved": True, "liquidity_approved": True,
                "frames": {"15m": {"last_closed_at_utc": NOW.isoformat()}}}
        result = evaluate(feed, NOW)
        self.assertEqual(result["signal"], "ELIGIBLE_FOR_PAPER_STRATEGY")
        self.assertFalse(result["execution_allowed"])
        self.assertEqual(result["timestamp_tehran"][-6:], "+03:30")

    def test_missing_timestamp_fails_closed(self):
        self.assertIn("MISSING_OR_INVALID_CANDLE_TIME", evaluate({"frames": {"15m": {}}}, NOW)["reasons"])

if __name__ == "__main__":
    unittest.main()
