import unittest
from tokenized_metals_registry import (
    METALS, RESEARCH_ONLY, SIGNALS_ENABLED, TRADING_ENABLED,
    TRADE_AUTHORIZED, research_watchlist, eligible_for_analysis,
    approved_market_pair,
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

    def test_trading_safety_locks(self):
        self.assertTrue(RESEARCH_ONLY)
        self.assertFalse(SIGNALS_ENABLED)
        self.assertFalse(TRADING_ENABLED)
        self.assertFalse(TRADE_AUTHORIZED)

if __name__ == "__main__":
    unittest.main()
