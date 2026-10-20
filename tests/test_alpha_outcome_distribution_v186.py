import unittest
from unittest.mock import patch
from engine.alpha_outcome_distribution_v186 import evaluate
def counts(touched=2,rejections=1,breakouts=1):
    return {'levels':3,'touched':touched,'confirmed_rejections':rejections,
      'confirmed_breakouts':breakouts,'ambiguous':0,'unresolved':0,'distinct_decisions':2}
def fixture(c):
    return {'subperiods':[{'part':1,'first_decision_epoch':0,
      'last_decision_epoch':14400,'counts':{'decision_windows':2,
      'by_band':{'LOW':c,'MEDIUM':counts(0,0,0),'HIGH':counts(0,0,0)}}}]}
class DistributionTests(unittest.TestCase):
    def test_counts_and_locks(self):
        with patch('engine.alpha_outcome_distribution_v186.subperiod',return_value=fixture(counts())):
            report=evaluate([])
        self.assertEqual(report['periods'][0]['bands']['LOW']['rejection_share_of_touches_descriptive'],.5)
        self.assertIsNone(report['periods'][0]['bands']['HIGH']['rejection_share_of_touches_descriptive'])
        self.assertTrue(report['research_only'])
        for key in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(report[key])
    def test_inconsistent_outcomes_rejected(self):
        with patch('engine.alpha_outcome_distribution_v186.subperiod',return_value=fixture(counts(2,1,0))):
            with self.assertRaisesRegex(ValueError,'OUTCOME_COUNT_MISMATCH'):evaluate([])
if __name__=='__main__':unittest.main()
