import unittest
from unittest.mock import patch
from engine.alpha_high_evidence_tiers_v189 import evaluate,tier
class EvidenceTierTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual([tier(x) for x in (0,4,5,9,10,20)],
          ['VERY_LIMITED','VERY_LIMITED','PRELIMINARY_REVIEW',
           'PRELIMINARY_REVIEW','DESCRIPTIVE_COMPARISON_ONLY','DESCRIPTIVE_COMPARISON_ONLY'])
    def test_invalid_count(self):
        for n in (-1,True,1.5):
            with self.assertRaisesRegex(ValueError,'INVALID_TOUCH_COUNT'):tier(n)
    def test_three_periods_and_safety(self):
        data={'periods':[{'part':i,'high_touches':n,'high_distinct_decisions':d}
            for i,n,d in ((1,1,9),(2,8,13),(3,10,16))]}
        with patch('engine.alpha_high_evidence_tiers_v189.guard',return_value=data):
            result=evaluate([])
        self.assertEqual([x['evidence_tier'] for x in result['periods']],
          ['VERY_LIMITED','PRELIMINARY_REVIEW','DESCRIPTIVE_COMPARISON_ONLY'])
        self.assertEqual([x['preliminary_review_allowed'] for x in result['periods']],[False,True,True])
        self.assertTrue(result['research_only'])
        self.assertEqual(result['signals'],[])
        for key in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(result[key])
if __name__=='__main__':unittest.main()
