"""RECOVERY-002: deterministic v5.3 replay and fail-closed evidence checks.

Synthetic snapshots prove code repeatability, NOT historical market reproducibility.
"""
import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path
from dual_screen_v53 import COINS, WEIGHTS, evaluate
from unified_guard_v548 import evaluate as guard_evaluate
from test_recovery_v55_parity import NOW, fixture

ROOT=Path(__file__).resolve().parents[1]

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),
       ensure_ascii=False).encode("utf-8")).hexdigest()

class RecoveryReplay(unittest.TestCase):
    def test_same_frozen_input_same_score_and_evidence(self):
        market=fixture()
        fingerprint=canonical_hash(market)
        a=evaluate("ETH",market,None,NOW)
        b=evaluate("ETH",deepcopy(market),None,NOW)
        self.assertEqual(a,b)
        self.assertEqual(fingerprint,canonical_hash(market))
        self.assertEqual(a["score"],sum(a["score_components"].values()))
        for key,weight in WEIGHTS.items():
            self.assertLessEqual(a["score_components"][key],weight)
            self.assertGreaterEqual(a["score_components"][key],0)

    def test_missing_cross_does_not_award_relative_strength(self):
        market=fixture()
        del market["pairs"]["ETHBTC"]
        result=evaluate("ETH",market,None,NOW)
        self.assertEqual(result["score_components"]["relative_btc"],0)
        self.assertIn("btc_cross_missing_or_stale",result["reasons"])

    def test_missing_btc_market_does_not_award_macro_points(self):
        market=fixture()
        del market["pairs"]["BTCUSDT"]
        result=evaluate("ETH",market,None,NOW)
        self.assertEqual(result["score_components"]["btc_and_dominance"],0)

    def test_guard_blocks_unverified_price_parity(self):
        market=fixture()
        market["pairs"]["BNBUSDT"]=deepcopy(market["pairs"]["ETHUSDT"])
        dual={"evaluations":[{"coin":"BNB","tier":"tier_1_priority_watch",
                              "score":95,"risk_reward_validated_levels":3}]}
        result=guard_evaluate(market,dual,{},{"pairs":{"BNB":{"status":"BLOCK"}}},NOW)
        self.assertEqual(result["coins"]["BNB"]["positive_publication_gate"],"BLOCK")
        self.assertIn("price_parity_unconfirmed",result["coins"]["BNB"]["reason_codes"])

    def test_guard_blocks_unverified_xrp_liquidity(self):
        market=fixture()
        market["pairs"]["XRPUSDT"]=deepcopy(market["pairs"]["ETHUSDT"])
        dual={"evaluations":[{"coin":"XRP","tier":"tier_1_priority_watch",
                              "score":95,"risk_reward_validated_levels":3}]}
        parity={"pairs":{"XRP":{"status":"PASS"}}}
        result=guard_evaluate(market,dual,{"status":"BLOCK"},parity,NOW)
        self.assertEqual(result["coins"]["XRP"]["positive_publication_gate"],"BLOCK")
        self.assertIn("xrp_btc_liquidity_unconfirmed",result["coins"]["XRP"]["reason_codes"])

    def test_historical_replay_not_claimed_without_raw_snapshot(self):
        path=ROOT/"data"/"multisource_market.json"
        self.assertTrue(path.exists())
        raw=path.read_bytes()
        self.assertGreater(len(raw),100,
            "Raw snapshot unavailable; historical score parity cannot be claimed")
        try:
            market=json.loads(raw)
        except (ValueError,UnicodeDecodeError) as exc:
            self.fail(f"Raw market snapshot is not valid JSON: {exc}")
        self.assertIsInstance(market,dict)
        self.assertIsInstance(market.get("pairs"),dict)
        self.assertIn("generated_at_utc",market)
        # This only establishes that raw evidence exists and is parseable.
        # A separately pinned SHA-256 and time-aligned replay are still required
        # before asserting parity with a published historical report.

if __name__=="__main__":
    unittest.main()
