import unittest
from unittest.mock import patch
from engine.alpha_decision_clusters_v192 import evaluate
B=(14400,10,12,9,11,100)
class ClusterTests(unittest.TestCase):
    def test_multiple_levels_same_decision_count_once(self):
        events=[{'decision_epoch':28800,'outcome':'CONFIRMED_REJECTION'},
          {'decision_epoch':28800,'outcome':'CONFIRMED_REJECTION'},
          {'decision_epoch':43200,'outcome':'NO_TOUCH'}]
        with patch('engine.alpha_decision_clusters_v192.replay',return_value={'events':events}):
            x=evaluate([B])
        self.assertEqual(x['level_observations'],3)
        self.assertEqual(x['decision_windows_with_candidates'],2)
        self.assertEqual(x['decision_windows_with_any_confirmed_rejection'],1)
        self.assertEqual(x['decision_windows_with_any_touch'],1)
        self.assertIsNone(x['signal_generation']['generated_signals'])
        self.assertEqual(x['signals'],[])
        self.assertTrue(x['research_only'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
    def test_unknown_outcome_rejected(self):
        with patch('engine.alpha_decision_clusters_v192.replay',return_value={'events':[{'decision_epoch':28800,'outcome':'UNKNOWN'}]}):
            with self.assertRaisesRegex(ValueError,'INVALID_OUTCOME'):evaluate([B])
    def test_invalid_decision_epoch(self):
        with patch('engine.alpha_decision_clusters_v192.replay',return_value={'events':[{'decision_epoch':True,'outcome':'NO_TOUCH'}]}):
            with self.assertRaisesRegex(ValueError,'INVALID_DECISION_EPOCH'):evaluate([B])
if __name__=='__main__':unittest.main()
