import unittest
from datetime import datetime, timedelta, timezone
from paired_historical_benchmark import compare

CUTOFF=datetime(2026,10,17,tzinfo=timezone.utc)
def candles():
    start=CUTOFF-timedelta(days=25)
    return [{"closed_at_utc":(start+timedelta(days=i)).isoformat(),
             "close":str(100 if i<25 else 120)} for i in range(30)]
def factors(score="0.75"):
    return {k:{"observed_at_utc":CUTOFF.isoformat(),"score":score,"source_verified":True}
            for k in ("trend","momentum","volume","macro")}

class PairedTests(unittest.TestCase):
    def test_baseline_runs_even_without_factors(self):
        r=compare(candles(),CUTOFF)
        self.assertIn("baseline",r)
        self.assertEqual(r["multifactor"]["status"],"NOT_EVALUABLE")
        self.assertFalse(r["execution_allowed"])

    def test_verified_factors_score(self):
        r=compare(candles(),CUTOFF,factors())
        self.assertEqual(r["multifactor"]["signal"],"BUY_PAPER")

    def test_future_factor_rejected(self):
        f=factors()
        f["macro"]["observed_at_utc"]=(CUTOFF+timedelta(days=1)).isoformat()
        self.assertEqual(compare(candles(),CUTOFF,f)["multifactor"]["reason"],"FUTURE_OR_UNDATED_FACTOR")

    def test_unverified_factor_rejected(self):
        f=factors()
        f["volume"]["source_verified"]=False
        self.assertEqual(compare(candles(),CUTOFF,f)["multifactor"]["reason"],"UNVERIFIED_FACTOR")

    def test_missing_factor_rejected(self):
        f=factors()
        del f["macro"]
        self.assertEqual(compare(candles(),CUTOFF,f)["multifactor"]["reason"],"MISSING_REQUIRED_FACTOR")

if __name__=="__main__":
    unittest.main()
