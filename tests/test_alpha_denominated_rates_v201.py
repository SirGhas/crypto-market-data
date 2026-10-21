import unittest
from unittest.mock import patch
from engine.alpha_denominated_rates_v201 import rates,evaluate
def p(part,n,m,k):return {'part':part,'candidate_decision_windows':n,
    'mixed_windows':m,'within_threshold_counts':{'1':k}}
class RatesTests(unittest.TestCase):
    def test_percentages_and_denominators(self):
        x=rates([p(1,20,5,2),p(2,30,6,3)])
        self.assertEqual(x['period_rates'][0]['mixed_share_of_candidate_windows_pct'],'25.00')
        self.assertEqual(x['period_rates'][0]['within_1_atr_share_of_mixed_pct'],'40.00')
        self.assertEqual(x['totals']['candidate_decision_windows'],50)
    def test_zero_mixed_is_null_conditional_share(self):
        x=rates([p(1,10,0,0)])
        self.assertIsNone(x['period_rates'][0]['within_1_atr_share_of_mixed_pct'])
    def test_invalid_counts_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'INVALID_DENOMINATOR_OR_COUNT'):
            rates([p(1,3,4,1)])
    def test_safety(self):
        with patch('engine.alpha_denominated_rates_v201.base_evaluate',return_value={
          'history_quality':{},'mixed_windows':1,'equal_duration_periods':[p(1,10,1,1)]}):
            x=evaluate([])
        self.assertEqual(x['signals'],[])
        self.assertIsNone(x['signal_generation']['generated_signals'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
