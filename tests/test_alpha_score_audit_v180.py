import unittest
from decimal import Decimal as D
from unittest.mock import patch
from engine.alpha_score_audit_v180 import evaluate
def bar(i):return (i*14400,D('100'),D('105'),D('95'),D('101'),D('100'))
class ScoreAuditTests(unittest.TestCase):
    def test_temporal_safety_and_flags(self):
        bars=[bar(i) for i in range(170)]
        snapshot={'candidates':[{'type':'resistance','body_level':'104',
                   'body_pivot_count':2,'confirmed_approach_rejections':1}]}
        with patch('engine.alpha_score_audit_v180.extract',return_value=snapshot):
            r=evaluate(bars)
        self.assertGreater(len(r['events']),0)
        self.assertTrue(all(e['historical_last_epoch']<e['decision_epoch'] for e in r['events']))
        self.assertEqual(sum(v['observations'] for v in r['groups'].values()),len(r['events']))
        self.assertEqual(r['signals'],[])
        for flag in ('signals_enabled','trading_enabled','trade_authorized',
                     'backtest_completed','continuous_freshness_proven','release_6_0_0_approved'):
            self.assertFalse(r[flag])
    def test_guard(self):
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT'):
            evaluate([bar(i) for i in range(60)])
    def test_non_contiguous(self):
        bars=[bar(i) for i in range(170)]
        bars[60]=bar(61)
        with self.assertRaisesRegex(ValueError,'NONCONTIGUOUS'):
            evaluate(bars)
if __name__=='__main__':unittest.main()
