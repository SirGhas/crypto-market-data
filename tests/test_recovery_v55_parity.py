"""RECOVERY-001: parity and sensitivity checks on the actual v5.3 engine."""
import unittest
from copy import deepcopy
from dual_screen_v53 import COINS, FRAMES, WEIGHTS, evaluate
from unified_guard_v548 import evaluate as guard_evaluate

NOW=1795000000

def frame(tf, *, trend=True, volume=1.0):
    sec=FRAMES[tf]
    end=((NOW-600)//sec)*sec
    start=end-234*sec
    candles=[]
    for i in range(234):
        price=100.0+(i*0.1 if trend else -i*0.1)
        candles.append({"t":start+i*sec,"o":price,"h":price+2,"l":price-2,
                        "c":price,"v":100.0})
    candles[-1]["v"]=100*volume
    return {"status":"available","source":"OKX Spot",
            "last_closed_at_utc":"synthetic-test-only",
            "candles":candles}

def fixture():
    frames={tf:frame(tf) for tf in FRAMES}
    return {"pairs":{"ETHUSDT":{"frames":frames},
                     "ETHBTC":{"frames":{"4h":frame("4h")}},
                     "BTCUSDT":{"frames":{"4h":frame("4h")}}}}

class RecoveryParity(unittest.TestCase):
    def test_weights_unchanged(self):
        self.assertEqual(WEIGHTS,{"static_levels":30,"volume":25,"trend_4h":15,
          "risk_reward":15,"relative_btc":5,"lower_timeframes":5,"btc_and_dominance":5})
        self.assertEqual(sum(WEIGHTS.values()),100)

    def test_volume_changes_only_volume_component(self):
        a=fixture(); b=deepcopy(a)
        b["pairs"]["ETHUSDT"]["frames"]["1h"]["candles"][-1]["v"]=250
        x=evaluate("ETH",a,None,NOW)
        y=evaluate("ETH",b,None,NOW)
        self.assertEqual(x["score_components"]["volume"]+5,y["score_components"]["volume"])
        for k in WEIGHTS:
            if k!="volume":
                self.assertEqual(x["score_components"][k],y["score_components"][k],k)

    def test_lower_timeframe_changes_lower_component_only(self):
        a=fixture();b=deepcopy(a)
        cs=b["pairs"]["ETHUSDT"]["frames"]["15m"]["candles"]
        cs[-1]["c"]=1
        x=evaluate("ETH",a,None,NOW)
        y=evaluate("ETH",b,None,NOW)
        self.assertEqual(x["score_components"]["lower_timeframes"]-2,y["score_components"]["lower_timeframes"])
        for k in WEIGHTS:
            if k!="lower_timeframes":
                self.assertEqual(x["score_components"][k],y["score_components"][k],k)

    def test_stale_frame_blocks(self):
        a=fixture()
        a["pairs"]["ETHUSDT"]["frames"]["4h"]["candles"][-1]["t"]-=30000
        x=evaluate("ETH",a,None,NOW)
        self.assertEqual(x["tier"],"blocked")
        self.assertIsNone(x["score"])

    def test_guard_rejects_noncontiguous_bars(self):
        a=fixture()
        a["pairs"]["ETHUSDT"]["frames"]["1h"]["candles"][-3]["t"]+=1
        dual={"evaluations":[{"coin":"ETH","tier":"tier_1_priority_watch",
                              "score":99,"risk_reward_validated_levels":3}]}
        r=guard_evaluate(a,dual,{}, {},NOW)
        self.assertEqual(r["coins"]["ETH"]["positive_publication_gate"],"BLOCK")
        self.assertIn("1h:noncontiguous",r["coins"]["ETH"]["reason_codes"])

    def test_no_synthetic_score_is_trade_authorization(self):
        a=fixture()
        x=evaluate("ETH",a,None,NOW)
        self.assertNotIn("trade_authorized",x)
        self.assertNotIn("order",x)

if __name__=="__main__":
    unittest.main()
