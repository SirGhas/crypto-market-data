import unittest
from decimal import Decimal as D
from unittest.mock import patch
from engine.alpha_score_audit_v181 import coverage,BINS
from engine.alpha_importance_v179 import score_level

def bar(i):
    return (i*14400,D('100'),D('105'),D('95'),D('101'),D('100'))

class ScoreCoverageTests(unittest.TestCase):
    def test_high_bin_reachable(self):
        self.assertEqual(score_level('4h',999,999),59)
        self.assertTrue(any(lo<=59<hi for _,lo,hi in BINS))
    def test_causal_replay_and_guards(self):
        bars=[bar(i) for i in range(170)]
        snap={'candidates':[{'type':'resistance','body_level':'104',
            'body_pivot_count':3,'confirmed_approach_rejections':2}]}
        with patch('engine.alpha_score_audit_v180.extract',return_value=snap):
            result=coverage(bars)
        self.assertGreater(result['groups']['HIGH']['observations'],0)
        self.assertEqual(sum(v['observations'] for v in result['groups'].values()),len(result['distinct_scores'])*result['groups']['HIGH']['observations'])
        self.assertFalse(result['trade_authorized'])
        self.assertFalse(result['signals_enabled'])
        self.assertEqual(result['signals'],[])
    def test_missing_history(self):
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT'):
            coverage([bar(i) for i in range(50)])
if __name__=='__main__':unittest.main()
