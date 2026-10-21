import unittest
from unittest.mock import patch
from engine.alpha_atr_sensitivity_v198 import sensitivity,evaluate
class SensitivityTests(unittest.TestCase):
    def test_threshold_monotonicity(self):
        x=sensitivity([{'nearest_pair_distance_atr':'0.25'},
          {'nearest_pair_distance_atr':'1.2'}])
        self.assertEqual(x['mixed_windows'],2)
        self.assertEqual(x['threshold_sensitivity'][1]['mixed_windows_within_threshold'],1)
        self.assertEqual(x['threshold_sensitivity'][-1]['mixed_windows_within_threshold'],2)
    def test_invalid_distance(self):
        with self.assertRaisesRegex(ValueError,'INVALID_ATR_DISTANCE'):
            sensitivity([{'nearest_pair_distance_atr':'NaN'}])
    def test_empty_counts(self):
        x=sensitivity([])
        self.assertTrue(all(v['mixed_windows_within_threshold']==0 for v in x['threshold_sensitivity']))
    def test_safety(self):
        with patch('engine.alpha_atr_sensitivity_v198.replay',return_value={'events':[]}):
            x=evaluate([(14400,10,12,9,11,100)])
        self.assertEqual(x['signals'],[])
        self.assertIsNone(x['signal_generation']['generated_signals'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
