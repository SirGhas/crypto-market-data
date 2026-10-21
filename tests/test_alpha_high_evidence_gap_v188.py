import unittest
from unittest.mock import patch
from engine.alpha_high_evidence_gap_v188 import evaluate
class GapTests(unittest.TestCase):
    def test_shortfall_and_locks(self):
        sample={'periods':[{'part':1,'high_touches':1,'high_distinct_decisions':9},
          {'part':2,'high_touches':20,'high_distinct_decisions':25}]}
        with patch('engine.alpha_high_evidence_gap_v188.guard',return_value=sample):
            out=evaluate([])
        self.assertEqual([x['touch_shortfall_to_descriptive_threshold'] for x in out['periods']],[19,0])
        self.assertFalse(out['all_periods_meet_count_threshold'])
        self.assertEqual(out['signals'],[])
        self.assertTrue(out['research_only'])
        for key in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(out[key])
    def test_negative_counts(self):
        sample={'periods':[{'part':1,'high_touches':-1,'high_distinct_decisions':0}]}
        with patch('engine.alpha_high_evidence_gap_v188.guard',return_value=sample):
            with self.assertRaisesRegex(ValueError,'NEGATIVE_COUNTS'):evaluate([])
if __name__=='__main__':unittest.main()
