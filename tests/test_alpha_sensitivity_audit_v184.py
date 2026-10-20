import unittest
from unittest.mock import patch
from engine.alpha_sensitivity_audit_v184 import evaluate
class SensitivityTests(unittest.TestCase):
    def test_empty(self):
        with self.assertRaisesRegex(ValueError,'EMPTY_SETTINGS'):evaluate([],())
    def test_duplicate(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_SETTING'):evaluate([],((6,6),(6,6)))
    def test_overlap(self):
        with self.assertRaisesRegex(ValueError,'INVALID_NONOVERLAP_SETTING'):evaluate([],((12,6),))
    def test_cases_and_safety(self):
        fake={'decision_windows_total':20,'train':{'decision_windows':12},
              'held_out':{'decision_windows':8}}
        with patch('engine.alpha_sensitivity_audit_v184.nonoverlap',return_value=fake) as m:
            result=evaluate([],((6,6),(12,12)))
        self.assertEqual(m.call_count,2)
        self.assertEqual(len(result['cases']),2)
        self.assertTrue(result['research_only'])
        self.assertFalse(result['signals_enabled'])
        self.assertFalse(result['trading_enabled'])
        self.assertFalse(result['trade_authorized'])
        self.assertFalse(result['release_6_0_0_approved'])
if __name__=='__main__':unittest.main()
