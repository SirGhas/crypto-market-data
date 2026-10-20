import unittest
from unittest.mock import patch
from engine.alpha_subperiod_audit_v185 import evaluate
class SubperiodTests(unittest.TestCase):
    def test_invalid_parts(self):
        with self.assertRaisesRegex(ValueError,'INVALID_PARTS'):evaluate([],parts=1)
    def test_overlapping(self):
        with self.assertRaisesRegex(ValueError,'OVERLAPPING_HORIZONS'):evaluate([],horizon=12,stride=6)
    def test_short_history(self):
        with patch('engine.alpha_subperiod_audit_v185.replay',return_value={'events':[]}):
            with self.assertRaisesRegex(ValueError,'INSUFFICIENT_DECISION_WINDOWS'):evaluate([])
    def test_chronology_and_locks(self):
        events=[{'decision_epoch':i*14400,'heuristic_score':50,'outcome':'NO_TOUCH'} for i in range(15)]
        with patch('engine.alpha_subperiod_audit_v185.replay',return_value={'events':events}):
            report=evaluate([],parts=3)
        self.assertEqual([p['counts']['decision_windows'] for p in report['subperiods']],[5,5,5])
        self.assertLess(report['subperiods'][0]['last_decision_epoch'],report['subperiods'][1]['first_decision_epoch'])
        self.assertTrue(report['research_only'])
        for flag in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(report[flag])
if __name__=='__main__':unittest.main()
