import unittest
from datetime import datetime,timedelta,timezone
from walkforward_audit import audit_window
START=datetime(2026,9,1,tzinfo=timezone.utc)
def candles(future=100):
    return [{"closed_at_utc":(START+timedelta(days=i)).isoformat(),
             "close":str(100+i if i<47 else future)} for i in range(65)]
class WalkforwardTests(unittest.TestCase):
    def test_every_predeclared_day_is_covered(self):
        r=audit_window(candles(),"2026-10-01","2026-10-31")
        self.assertEqual(r["days_checked"],31)
        self.assertEqual(r["signal_days"]+r["no_signal_days"],31)
    def test_future_does_not_change_decisions(self):
        a=audit_window(candles(100),"2026-10-01","2026-10-10")
        b=audit_window(candles(9999),"2026-10-01","2026-10-10")
        self.assertEqual([e["signal"] for e in a["events"]],[e["signal"] for e in b["events"]])
    def test_invalid_dates(self):
        with self.assertRaises(ValueError):
            audit_window(candles(),"2026-10-31","2026-10-01")
    def test_no_signal_not_a_loss(self):
        r=audit_window(candles(),"2026-10-01","2026-10-10")
        self.assertEqual(r["wins"]+r["losses"]+r["flats"],r["evaluated_signals"])
if __name__=="__main__":
    unittest.main()
