import unittest
from unittest.mock import patch
from engine.alpha_high_sample_guard_v187 import evaluate
def fixture(n):
    return {'periods':[{'part':i+1,'bands':{'HIGH':{
       'touched':v,'distinct_decisions':v+1,'confirmed_rejections':0,
       'confirmed_breakouts':0}}} for i,v in enumerate(n)]}
class HighGuardTests(unittest.TestCase):
    def test_invalid_threshold(self):
        for n in (0,-1,True):
            with self.assertRaisesRegex(ValueError,'INVALID_MINIMUM_TOUCHES'):
                evaluate([],minimum_touches=n)
    def test_low_samples_are_not_validated(self):
        with patch('engine.alpha_high_sample_guard_v187.distribution',return_value=fixture([1,9,19])):
            out=evaluate([])
        self.assertFalse(out['all_periods_meet_count_threshold'])
        self.assertTrue(all(x['sample_sufficiency']=='INSUFFICIENT' for x in out['periods']))
        self.assertTrue(out['research_only'])
        self.assertEqual(out['signals'],[])
        for key in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(out[key])
    def test_count_threshold_does_not_claim_validation(self):
        with patch('engine.alpha_high_sample_guard_v187.distribution',return_value=fixture([20,30])):
            out=evaluate([])
        self.assertTrue(out['all_periods_meet_count_threshold'])
        self.assertEqual(out['periods'][0]['sample_sufficiency'],'COUNT_THRESHOLD_MET_NOT_VALIDATED')
if __name__=='__main__':unittest.main()
