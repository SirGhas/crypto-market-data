import unittest
from phemex_slvon_probe import find_spot_product, validate_rows, probe


class PhemexSLVONProbeTests(unittest.TestCase):
    def test_only_spot_accepted(self):
        with self.assertRaisesRegex(ValueError, "NOT_UNAMBIGUOUS"):
            find_spot_product({"data": {"products": [{"symbol": "sSLVONUSDT", "type": "Perpetual"}]}})

    def test_valid_spot_identity(self):
        self.assertEqual(find_spot_product({"data": {"products": [
            {"symbol": "sSLVONUSDT", "type": "Spot"}]}})["symbol"], "sSLVONUSDT")

    def test_malformed_candle_rejected(self):
        with self.assertRaisesRegex(ValueError, "MALFORMED"):
            validate_rows([[0, 900]], 900, 1000000)

    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError, "NONFINITE"):
            validate_rows([[0, 900, 1, 1, 2, 0.5, float("nan"), 1, 1]], 900, 1000000)

    def test_unaligned_rejected(self):
        with self.assertRaisesRegex(ValueError, "ALIGNMENT"):
            validate_rows([[1, 900, 1, 1, 2, 0.5, 1, 1, 1]], 900, 1000000)

    def test_short_history_rejected(self):
        with self.assertRaisesRegex(ValueError, "INSUFFICIENT"):
            validate_rows([[0, 900, 1, 1, 2, 0.5, 1, 1, 1]], 900, 1000000)

    def test_gap_rejected(self):
        rows = [[i*900, 900, 1, 1, 2, 0.5, 1, 1, 1] for i in range(234) if i != 100]
        with self.assertRaisesRegex(ValueError, "HISTORY_GAP"):
            validate_rows(rows, 900, 234*900+3)

    def test_complete_history_validates_but_does_not_approve_feed(self):
        rows = [[i*900, 900, 1, 1, 2, 0.5, 1, 1, 1] for i in range(233)]
        result = validate_rows(rows, 900, 233*900+3)
        self.assertEqual(result["closed_candles"], 233)
        self.assertTrue(result["scaled_prices_not_yet_normalized"])

    def test_probe_fails_closed_on_network_error(self):
        from unittest.mock import patch
        with patch("phemex_slvon_probe.get_json", side_effect=OSError("offline")):
            result = probe(now=1000000)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["trading_enabled"])
        self.assertFalse(result["analysis_enabled"])


if __name__ == "__main__":
    unittest.main()
