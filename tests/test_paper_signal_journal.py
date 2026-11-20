import unittest
from datetime import datetime, timezone
from paper_signal_journal import make_record, append_unique

NOW = datetime(2026, 11, 17, 15, 30, tzinfo=timezone.utc)
GATE = {"signal": "ELIGIBLE_FOR_PAPER_STRATEGY", "reasons": [], "execution_allowed": False}

class JournalTests(unittest.TestCase):
    def test_deterministic_event_id(self):
        a = make_record("BTC", "baseline", GATE, "BUY_PAPER", "95000", NOW)
        self.assertEqual(a, make_record("BTC", "baseline", GATE, "BUY_PAPER", "95000", NOW))
        self.assertFalse(a["execution_allowed"])

    def test_no_trade_without_approved_gate(self):
        with self.assertRaisesRegex(ValueError, "PAPER_GATE_NOT_APPROVED"):
            make_record("SLVON", "baseline", {"signal": "NO_SIGNAL", "execution_allowed": False},
                        "BUY_PAPER", "42", NOW)

    def test_no_live_execution_even_when_gate_eligible(self):
        with self.assertRaisesRegex(ValueError, "EXECUTION_MUST_BE_DISABLED"):
            make_record("BTC", "baseline", {"signal": "ELIGIBLE_FOR_PAPER_STRATEGY",
                                            "execution_allowed": True}, "BUY_PAPER", "95000", NOW)

    def test_duplicate_event_not_appended(self):
        item = make_record("BTC", "baseline", GATE, "WATCH", "95000", NOW)
        self.assertEqual(len(append_unique(append_unique([], item), item)), 1)

    def test_nonfinite_price_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_REFERENCE_PRICE"):
            make_record("BTC", "baseline", GATE, "WATCH", "NaN", NOW)

if __name__ == "__main__":
    unittest.main()
