import unittest
from tokenized_metals_registry import (
    METALS, RESEARCH_ONLY, SIGNALS_ENABLED, TRADING_ENABLED,
    TRADE_AUTHORIZED, research_watchlist, eligible_for_analysis,
    approved_market_pair, silver_price_snapshot,
)

class TokenizedMetalsRegistryTests(unittest.TestCase):
    def test_requested_symbols_are_recorded(self):
        self.assertEqual(research_watchlist(), ("XAUT", "SLVON"))

    def test_gold_identity_and_quote(self):
        self.assertEqual(METALS["XAUT"].market_pair, "XAUT-USDT")
        self.assertEqual(METALS["XAUT"].venue, "OKX Spot")

    def test_silver_phemex_spot_listing_is_registered(self):
        self.assertEqual(METALS["SLVON"].market_pair, "SLVON/USDT")
        self.assertEqual(METALS["SLVON"].venue, "Phemex Spot")
        self.assertTrue(METALS["SLVON"].identity_verified)

    def test_both_assets_fail_closed_until_data_validation(self):
        for ticker in research_watchlist():
            self.assertFalse(eligible_for_analysis(ticker))
            with self.assertRaisesRegex(ValueError, "METAL_RESEARCH_FEED_NOT_APPROVED"):
                approved_market_pair(ticker)

    def test_restricted_silver_snapshot(self):
        evidence = {"asset": "SLVON", "venue": "Phemex Spot",
                    "status": "PRICE_SCALE_VERIFIED_VOLUME_SCALE_AND_REFERENCE_PARITY_PENDING",
                    "frames": {"15m": {"latest_normalized_close_usdt": "36.5",
                                       "last_closed_at_tehran": "2026-11-25T09:30:00+03:30"}}}
        result = silver_price_snapshot(evidence)
        self.assertEqual(result["close_usdt"], "36.5")
        for key in ("volume_enabled", "reference_parity_enabled", "analysis_enabled",
                    "signals_enabled", "trading_enabled"):
            self.assertFalse(result[key])
        evidence["status"] = "BLOCKED"
        with self.assertRaisesRegex(ValueError, "SLVON_PRICE_NOT_VALIDATED"):
            silver_price_snapshot(evidence)

    def test_trading_safety_locks(self):
        self.assertTrue(RESEARCH_ONLY)
        self.assertFalse(SIGNALS_ENABLED)
        self.assertFalse(TRADING_ENABLED)
        self.assertFalse(TRADE_AUTHORIZED)

if __name__ == "__main__":
    unittest.main()
