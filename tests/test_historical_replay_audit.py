import unittest
from datetime import datetime, timedelta, timezone
from historical_replay_audit import replay_audit

CUTOFF = datetime(2026, 10, 17, tzinfo=timezone.utc)

class HistoricalReplayAuditTests(unittest.TestCase):
    def test_future_candles_hidden(self):
        candles = [{"closed_at_utc": (CUTOFF + timedelta(days=d)).isoformat(),
                    "close": str(100+d)} for d in (-2,-1,0,1,2)]
        r = replay_audit(candles, CUTOFF, min_history=3)
        self.assertEqual(r["visible_candles"], 3)
        self.assertEqual(r["hidden_future_candles"], 2)
        self.assertEqual(r["visible_last_close"], "100")
        self.assertTrue(r["ready_for_signal_evaluation"])
        self.assertFalse(r["execution_allowed"])

    def test_insufficient_history_not_approved(self):
        r = replay_audit([], CUTOFF)
        self.assertEqual(r["status"], "INSUFFICIENT_HISTORY")

    def test_duplicate_candles_rejected(self):
        c = {"closed_at_utc": CUTOFF.isoformat(), "close": "100"}
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            replay_audit([c,c], CUTOFF)

    def test_invalid_close_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_HISTORICAL_CANDLE"):
            replay_audit([{"closed_at_utc": CUTOFF.isoformat(), "close": "NaN"}], CUTOFF)

if __name__ == "__main__":
    unittest.main()
