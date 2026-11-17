import unittest
from datetime import datetime, timedelta, timezone
from causal_sma_backtest import run_backtest

START=datetime(2026,10,1,tzinfo=timezone.utc)
def series(values):
    return [{"closed_at_utc":(START+timedelta(days=i)).isoformat(),"close":str(v)}
            for i,v in enumerate(values)]

class CausalBacktestTests(unittest.TestCase):
    def test_future_price_cannot_change_signal(self):
        before=[100]*20+[120]
        cutoff=START+timedelta(days=20)
        a=run_backtest(series(before+[140,150]),cutoff,fast=3,slow=10,horizon=1)
        b=run_backtest(series(before+[40,30]),cutoff,fast=3,slow=10,horizon=1)
        self.assertEqual(a["signal"],"BUY_PAPER")
        self.assertEqual(a["signal"],b["signal"])
        self.assertNotEqual(a["net_return_pct"],b["net_return_pct"])
        self.assertFalse(a["execution_allowed"])

    def test_no_signal_is_not_a_win(self):
        r=run_backtest(series([100]*26),START+timedelta(days=20),fast=3,slow=10)
        self.assertEqual(r["signal"],"NO_SIGNAL")
        self.assertFalse(r["evaluated"])

    def test_missing_future_is_not_a_success(self):
        r=run_backtest(series([100]*20+[120]),START+timedelta(days=20),fast=3,slow=10)
        self.assertEqual(r["reason"],"INSUFFICIENT_POST_CUTOFF_HISTORY")
        self.assertFalse(r["evaluated"])

    def test_duplicate_timestamps_rejected(self):
        c=series([100])[0]
        with self.assertRaisesRegex(ValueError,"DUPLICATE_TIMESTAMP"):
            run_backtest([c,c],START)

    def test_short_crossing(self):
        r=run_backtest(series([100]*20+[80,70]),START+timedelta(days=20),
                       fast=3,slow=10,horizon=1)
        self.assertEqual(r["signal"],"SELL_PAPER")
        self.assertEqual(r["outcome"],"WIN")

    def test_insufficient_pre_cutoff_history(self):
        r=run_backtest(series([100]*5),START+timedelta(days=4),fast=3,slow=10)
        self.assertEqual(r["reason"],"INSUFFICIENT_PRE_CUTOFF_HISTORY")

if __name__=="__main__":
    unittest.main()
