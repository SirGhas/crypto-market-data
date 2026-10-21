import unittest
from unittest.mock import patch
from engine.alpha_mixed_sides_v194 import analyze,evaluate
def e(epoch,side,outcome):return {'decision_epoch':epoch,'side':side,'outcome':outcome}
R='CONFIRMED_REJECTION';B='CONFIRMED_CLOSE_THROUGH'
class MixedSidesTests(unittest.TestCase):
    def test_mixed_across_sides(self):
        x=analyze([e(1,'support',R),e(1,'resistance',B)])
        self.assertEqual(x['mixed_outcome_details']['mixed_windows'],1)
        self.assertEqual(x['mixed_outcome_details']['mixed_across_sides'],1)
        self.assertEqual(x['mixed_outcome_details']['mixed_within_support'],0)
    def test_mixed_within_side(self):
        x=analyze([e(1,'support',R),e(1,'support',B)])
        self.assertEqual(x['mixed_outcome_details']['mixed_across_sides'],0)
        self.assertEqual(x['mixed_outcome_details']['mixed_within_support'],1)
    def test_reject_invalid_side(self):
        with self.assertRaisesRegex(ValueError,'INVALID_SIDE'):
            analyze([e(1,'other',R)])
    def test_safety_flags(self):
        with patch('engine.alpha_mixed_sides_v194.replay',return_value={'events':[]}):
            x=evaluate([(14400,10,12,9,11,100)])
        self.assertEqual(x['signals'],[])
        self.assertIsNone(x['signal_generation']['generated_signals'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
