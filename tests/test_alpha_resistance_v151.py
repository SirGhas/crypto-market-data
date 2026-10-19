import copy
import unittest
from engine.alpha_resistance_v151 import resistance_gate,overlay

def fixture():
    market={'timeframes':{'4h':{'status':'VALIDATED','close':'100','candle_direction':'DOWN','rvol20':'4',
                               'broke_resistance_20':False},
                           '1D':{'status':'VALIDATED','sma_close':{'SMA233':{'close_above':True,'slope':'UP'}}}},
            'risk_v15':{'hypothetical_stop':'94','data_validation':{'matched_report_candle_identities':True}}}
    old={'4h_overhead_resistance_levels':{'20':'104','60':'120'},'daily_overhead_resistance_levels':{'20':'112'}}
    return market,old
class ResistanceTests(unittest.TestCase):
    def test_nearest_resistance_blocks_2r(self):
        m,o=fixture();g=resistance_gate('TEST',m,o)
        self.assertEqual(g['gross_rr_to_first_resistance'],'0.66666667')
        self.assertIn('FIRST_RESISTANCE_BLOCKS_MINIMUM_2R',g['blocking_reasons'])
        self.assertEqual(g['first_daily_resistance'],'112')
        self.assertFalse(g['targets_clear_first_resistance']['2'])
    def test_overhead_wider_allows_2r_but_not_trade(self):
        m,o=fixture();o['4h_overhead_resistance_levels']={'20':'118'}
        g=resistance_gate('TEST',m,o)
        self.assertEqual(g['gross_rr_to_first_resistance'],'2')
        self.assertTrue(g['targets_clear_first_resistance']['2'])
        self.assertFalse(g['trade_authorized'])
    def test_large_bear_volume_not_breakout(self):
        m,o=fixture();m['timeframes']['4h']['broke_resistance_20']=True
        self.assertFalse(resistance_gate('TEST',m,o)['breakout_watch'])
    def test_breakout_only_watch_without_retest(self):
        m,o=fixture();m['timeframes']['4h']['candle_direction']='UP';m['timeframes']['4h']['broke_resistance_20']=True
        g=resistance_gate('TEST',m,o)
        self.assertTrue(g['breakout_watch']);self.assertFalse(g['breakout_validated'])
        self.assertIn('BREAKOUT_RETEST_AND_HISTORICAL_LEVEL_NOT_VALIDATED',g['blocking_reasons'])
    def test_missing_daily_resistance_blocks(self):
        m,o=fixture();o['daily_overhead_resistance_levels']={}
        self.assertIn('NO_DAILY_OVERHEAD_RESISTANCE',resistance_gate('TEST',m,o)['blocking_reasons'])
    def test_missing_atr_blocks(self):
        m,o=fixture();m['risk_v15']={'hypothetical_stop':None}
        self.assertIsNone(resistance_gate('TEST',m,o)['gross_rr_to_first_resistance'])
    def test_version_trade_guards(self):
        m,o=fixture();r=overlay({'version':'alpha-1.5-causal-risk-research','assets':{'TEST':m},'risk_research':{'TEST':o}})
        self.assertFalse(r['trading_enabled']);self.assertEqual(r['signals'],[])
        self.assertFalse(r['continuous_freshness_proven']);self.assertFalse(r['assets']['TEST']['trade_authorized'])
    def test_input_unmodified(self):
        m,o=fixture();r={'version':'alpha-1.5-causal-risk-research','assets':{'TEST':m},'risk_research':{'TEST':o}}
        snap=copy.deepcopy(r);overlay(r);self.assertEqual(r,snap)

if __name__=='__main__':unittest.main()
