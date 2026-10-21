import unittest
from unittest.mock import patch
from engine.alpha_window_outcomes_v193 import categorize,evaluate
def w(t=False,r=False,b=False):
    return {'any_touch':t,'any_confirmed_rejection':r,'any_confirmed_breakout':b}
class ExclusiveOutcomeTests(unittest.TestCase):
    def test_exclusive_partition(self):
        x=categorize([w(),w(True),w(True,True),w(True,False,True),w(True,True,True)])
        self.assertEqual(x,{'rejection_only':1,'breakout_only':1,
          'both_rejection_and_breakout':1,'touch_without_confirmed_direction':1,'no_touch':1})
    def test_impossible_confirmation(self):
        with self.assertRaisesRegex(ValueError,'CONFIRMATION_WITHOUT_TOUCH'):
            categorize([w(False,True)])
    def test_aggregation_and_safety(self):
        windows=[w(),w(True,True),w(True,True,True)]
        base={'windows':windows,'history_quality':{},
          'decision_windows_with_any_confirmed_rejection':2,
          'decision_windows_with_any_confirmed_breakout':1,
          'decision_windows_with_any_touch':2}
        with patch('engine.alpha_window_outcomes_v193.clusters',return_value=base):
            out=evaluate([])
        self.assertEqual(sum(out['mutually_exclusive_window_counts'].values()),3)
        self.assertIsNone(out['signal_generation']['generated_signals'])
        self.assertEqual(out['signals'],[])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(out[k])
    def test_inconsistent_counts(self):
        base={'windows':[w(True,True)],'history_quality':{},
          'decision_windows_with_any_confirmed_rejection':0,
          'decision_windows_with_any_confirmed_breakout':0,
          'decision_windows_with_any_touch':1}
        with patch('engine.alpha_window_outcomes_v193.clusters',return_value=base):
            with self.assertRaisesRegex(ValueError,'REJECTION_COUNT_MISMATCH'):evaluate([])
if __name__=='__main__':unittest.main()
