import unittest
from unittest.mock import patch
from engine.alpha_equal_duration_v200 import equal_duration,evaluate
def row(t,d):return {'decision_epoch':t,'nearest_pair_distance_atr':str(d)}
class EqualDurationTests(unittest.TestCase):
    def test_calendar_partition_reconciles(self):
        x=equal_duration([row(0,'0.2'),row(30,'1.5'),row(60,'2')],[0,10,20,30,40,50,60])
        self.assertEqual(sum(p['mixed_windows'] for p in x),3)
        self.assertEqual(sum(p['candidate_decision_windows'] for p in x),7)
    def test_empty_period_has_null_median(self):
        x=equal_duration([row(0,'0.2')],[0,30,60])
        self.assertIsNone(x[1]['median_distance_atr'])
    def test_reject_mixed_outside_decisions(self):
        with self.assertRaisesRegex(ValueError,'MIXED_OUTSIDE_DECISIONS'):
            equal_duration([row(5,'1')],[0,10,20])
    def test_safety(self):
        with patch('engine.alpha_equal_duration_v200.replay',return_value={
            'events':[{'decision_epoch':t} for t in (0,30,60)]}),patch(
          'engine.alpha_equal_duration_v200.analyze',return_value={
            'details':[row(t,'1') for t in (0,30,60)],'counts':{'mixed_windows':3}}):
            x=evaluate([(14400,10,12,9,11,100)])
        self.assertEqual(x['signals'],[])
        self.assertIsNone(x['signal_generation']['generated_signals'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
