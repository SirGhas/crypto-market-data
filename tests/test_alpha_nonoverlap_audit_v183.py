import unittest
from decimal import Decimal as D
from unittest.mock import patch
from engine.alpha_nonoverlap_audit_v183 import evaluate

def bar(i):
    return (i*14400,D('100'),D('105'),D('95'),D('101'),D('100'))

class NonoverlapTests(unittest.TestCase):
    def test_no_overlapping_horizons(self):
        with self.assertRaisesRegex(ValueError,'OVERLAPPING_FUTURE_HORIZONS'):
            evaluate([],horizon=12,stride=6)
    def test_causal_split_and_safety(self):
        snap={'candidates':[{'type':'resistance','body_level':'104',
             'body_pivot_count':3,'confirmed_approach_rejections':2}]}
        with patch('engine.alpha_score_audit_v180.extract',return_value=snap):
            data=evaluate([bar(i) for i in range(270)])
        self.assertGreater(data['train']['decision_windows'],0)
        self.assertGreater(data['held_out']['decision_windows'],0)
        self.assertEqual(data['signals'],[])
        self.assertFalse(data['trading_enabled'])
        self.assertFalse(data['trade_authorized'])
        self.assertFalse(data['release_6_0_0_approved'])
if __name__=='__main__':unittest.main()
