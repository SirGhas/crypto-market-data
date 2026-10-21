import unittest
from unittest.mock import patch
from engine.alpha_level_recurrence_v203 import recurrence,evaluate
def e(t,side,level):return {'decision_epoch':t,'side':side,'level':level}
class RecurrenceTests(unittest.TestCase):
    def test_exact_identity_and_consecutive_reuse(self):
        x=recurrence([e(1,'support','100.00'),e(2,'support','100'),
          e(2,'resistance','100'),e(3,'support','100'),e(4,'support','101')])['counts']
        self.assertEqual(x['unique_exact_level_identities'],3)
        self.assertEqual(x['identities_in_three_or_more_windows'],1)
        self.assertEqual(x['consecutive_window_identity_links'],2)
        self.assertEqual(x['windows_with_identity_seen_in_prior_window'],2)
    def test_same_window_not_multiple_windows(self):
        x=recurrence([e(1,'support','100'),e(1,'support','100.0')])['counts']
        self.assertEqual(x['identities_in_multiple_windows'],0)
    def test_invalid_level(self):
        with self.assertRaisesRegex(ValueError,'INVALID_LEVEL'):
            recurrence([e(1,'support','NaN')])
    def test_safety(self):
        with patch('engine.alpha_level_recurrence_v203.replay',return_value={'events':[]}):
            x=evaluate([(14400,10,12,9,11,100)])
        self.assertEqual(x['signals'],[])
        self.assertIsNone(x['signal_generation']['generated_signals'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
