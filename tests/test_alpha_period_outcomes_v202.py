import unittest
from unittest.mock import patch
from engine.alpha_period_outcomes_v202 import partition,evaluate
def w(t,touch=False,reject=False,breakout=False):
    return {'decision_epoch':t,'any_touch':touch,'any_confirmed_rejection':reject,
      'any_confirmed_breakout':breakout}
def p(a,b,n,part=1):return {'part':part,'start_epoch_inclusive':a,'end_epoch_exclusive':b,
  'candidate_decision_windows':n}
class PeriodOutcomeTests(unittest.TestCase):
    def test_overlap_not_double_counted_in_partition(self):
        x=partition([w(1,True,True,True),w(2,True,True),w(3)],
          [p(0,4,3)])[0]
        self.assertEqual(x['exclusive_outcomes']['both_rejection_and_breakout'],1)
        self.assertEqual(x['overlapping_event_window_counts']['any_confirmed_rejection'],2)
        self.assertEqual(x['event_window_share_pct']['any_touch'],'66.67')
    def test_denominator_guard(self):
        with self.assertRaisesRegex(ValueError,'PERIOD_DENOMINATOR_MISMATCH'):
            partition([w(1)],[p(0,4,2)])
    def test_coverage_guard(self):
        with self.assertRaisesRegex(ValueError,'WINDOW_COVERAGE_MISMATCH'):
            partition([w(1),w(5)],[p(0,4,1)])
    def test_safety(self):
        with patch('engine.alpha_period_outcomes_v202.duration_evaluate',return_value={
          'history_quality':{},'mixed_windows':0,'equal_duration_periods':[p(0,4,1)]}),patch(
          'engine.alpha_period_outcomes_v202.clusters',return_value={'windows':[w(1)]}):
            x=evaluate([])
        self.assertEqual(x['signals'],[])
        self.assertIsNone(x['signal_generation']['generated_signals'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
