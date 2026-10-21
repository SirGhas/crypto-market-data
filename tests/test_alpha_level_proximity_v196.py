import unittest
from unittest.mock import patch
from engine.alpha_level_proximity_v196 import proximity,evaluate
def e(t,s,p,o):return {'decision_epoch':t,'side':s,'level':p,'outcome':o}
R='CONFIRMED_REJECTION';B='CONFIRMED_CLOSE_THROUGH'
class ProximityTests(unittest.TestCase):
    def test_close_pair(self):
        x=proximity([e(1,'support','100',R),e(1,'support','100.05',B)])
        self.assertEqual(x['counts']['mixed_windows'],1)
        self.assertEqual(x['counts']['mixed_windows_with_pair_within_0.100pct'],1)
        self.assertEqual(x['counts']['same_side_nearest_pair_windows'],1)
    def test_far_pair(self):
        x=proximity([e(1,'support','100',R),e(1,'resistance','110',B)])
        self.assertEqual(x['counts']['mixed_windows_with_pair_within_1.00pct'],0)
        self.assertEqual(x['counts']['opposite_side_nearest_pair_windows'],1)
    def test_invalid_price(self):
        with self.assertRaisesRegex(ValueError,'INVALID_LEVEL'):
            proximity([e(1,'support','NaN',R)])
    def test_safety(self):
        with patch('engine.alpha_level_proximity_v196.replay',return_value={'events':[]}):
            x=evaluate([(14400,10,12,9,11,100)])
        self.assertEqual(x['signals'],[])
        self.assertIsNone(x['signal_generation']['generated_signals'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
