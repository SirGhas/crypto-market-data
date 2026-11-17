import unittest
from datetime import datetime,timedelta,timezone
from ohlcv_factor_evidence import evidence_from_ohlcv
START=datetime(2026,9,1,tzinfo=timezone.utc)
def rows(future=999):
    out=[]
    for i in range(55):
        p=100+i if i<47 else future
        out.append({"closed_at_utc":(START+timedelta(days=i)).isoformat(),
                    "close":str(p),"high":str(p+2),"low":str(p-2),"volume":str(1000+i)})
    return out
class EvidenceTests(unittest.TestCase):
    def test_future_cannot_change_factors(self):
        cutoff=START+timedelta(days=46)
        a=evidence_from_ohlcv(rows(100),cutoff,"fixture")
        b=evidence_from_ohlcv(rows(99999),cutoff,"fixture")
        self.assertEqual(a,b)
        self.assertEqual(set(a),{"momentum","volume_liquidity","multi_timeframe"})
    def test_reject_invalid_candle(self):
        r=rows()
        r[1]["low"]="9999"
        with self.assertRaisesRegex(ValueError,"INVALID_OHLCV"):
            evidence_from_ohlcv(r,START+timedelta(days=46),"fixture")
    def test_insufficient_history(self):
        self.assertEqual(evidence_from_ohlcv(rows(),START+timedelta(days=2),"fixture"),{})
if __name__=="__main__":
    unittest.main()
