import unittest
from unittest.mock import patch
from engine.alpha_transparent_counts_v191 import evaluate
B=(14400,10,12,9,11,100)
def band(levels,touched,rej=0,brk=0,amb=0,unres=0):
    return {'levels':levels,'touched':touched,'confirmed_rejections':rej,
      'confirmed_breakouts':brk,'ambiguous':amb,'unresolved':unres}
def source():
    return {'periods':[{'part':1,'bands':{'LOW':band(5,2,1,1),
      'MEDIUM':band(3,1,0,0,1),'HIGH':band(2,1,0,0,0,1)}}]}
class TransparentCountTests(unittest.TestCase):
    def test_counts_not_signals(self):
        with patch('engine.alpha_transparent_counts_v191.distribution',return_value=source()):
            out=evaluate([B])
        self.assertEqual(out['totals']['identified_level_observations'],10)
        self.assertEqual(out['totals']['historical_touches'],4)
        self.assertEqual(out['totals']['historical_confirmed_rejections'],1)
        self.assertEqual(out['totals']['historical_no_touch'],6)
        self.assertIsNone(out['signal_generation']['generated_signals'])
        self.assertEqual(out['signal_generation']['status'],'DISABLED_BY_SAFETY_POLICY')
        self.assertTrue(out['research_only'])
        self.assertEqual(out['signals'],[])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(out[k])
    def test_bad_outcome_accounting(self):
        bad=source();bad['periods'][0]['bands']['LOW']['touched']=3
        with patch('engine.alpha_transparent_counts_v191.distribution',return_value=bad):
            with self.assertRaisesRegex(ValueError,'INCONSISTENT_RESEARCH_OUTCOMES'):
                evaluate([B])
    def test_bad_level_count(self):
        bad=source();bad['periods'][0]['bands']['HIGH']['levels']=0
        with patch('engine.alpha_transparent_counts_v191.distribution',return_value=bad):
            with self.assertRaisesRegex(ValueError,'INVALID_RESEARCH_COUNTS'):
                evaluate([B])
if __name__=='__main__':unittest.main()
