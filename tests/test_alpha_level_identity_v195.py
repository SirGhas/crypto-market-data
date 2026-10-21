import unittest
from unittest.mock import patch
from engine.alpha_level_identity_v195 import summarize,evaluate
def e(t,s,p,o):return {'decision_epoch':t,'side':s,'level':p,'outcome':o}
R='CONFIRMED_REJECTION';B='CONFIRMED_CLOSE_THROUGH'
class LevelIdentityTests(unittest.TestCase):
    def test_exact_decimal_identity_conflict(self):
        x=summarize([e(1,'support','100.00',R),e(1,'support','100.0',B)])
        self.assertEqual(x['mixed_with_same_level_identity'],1)
        self.assertEqual(x['mixed_only_across_different_level_identities'],0)
    def test_different_level_not_conflict(self):
        x=summarize([e(1,'support','100',R),e(1,'support','101',B)])
        self.assertEqual(x['mixed_with_same_level_identity'],0)
        self.assertEqual(x['mixed_only_across_different_level_identities'],1)
    def test_side_part_of_identity(self):
        x=summarize([e(1,'support','100',R),e(1,'resistance','100',B)])
        self.assertEqual(x['mixed_with_same_level_identity'],0)
    def test_invalid_level(self):
        with self.assertRaisesRegex(ValueError,'INVALID_LEVEL'):
            summarize([e(1,'support','NaN',R)])
    def test_safety(self):
        with patch('engine.alpha_level_identity_v195.replay',return_value={'events':[]}):
            x=evaluate([(14400,10,12,9,11,100)])
        self.assertEqual(x['signals'],[])
        self.assertIsNone(x['signal_generation']['generated_signals'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
