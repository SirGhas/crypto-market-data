import unittest
from copy import deepcopy
from engine.alpha_swing_run_v162 import UNIVERSE, benchmark_overlay

class TestBTCBenchmark(unittest.TestCase):
    def report(self):
        assets={}
        for asset in UNIVERSE:
            assets[asset]={'timeframes':{
                '4h':{'status':'VALIDATED','identity':'1792000000:240','close':'100' if asset!='BTC' else '60000'},
                '1D':{'status':'VALIDATED','identity':'1791936000:1440','close':'105' if asset!='BTC' else '61000'}}}
        return {'assets':assets,'totals':{},'signals':[],'trading_enabled':False}
    def test_exactly_11_including_btc(self):
        self.assertEqual(len(UNIVERSE),11)
        self.assertIn('BTC',UNIVERSE)
        self.assertEqual(len(benchmark_overlay(self.report())['assets']),11)
    def test_relative_price_is_not_return(self):
        r=benchmark_overlay(self.report())
        e=r['btc_relative_price_research']['ETH']
        self.assertEqual(e['status'],'SYNCHRONIZED_SPOT_RELATIVE_PRICE_RESEARCH')
        self.assertEqual(e['timeframes']['4h']['relative_price_in_btc'],'0.001666666667')
        self.assertIn('RELATIVE_PRICE_LEVEL_NOT_RELATIVE_PERFORMANCE',e['limitations'])
    def test_btc_must_have_valid_closed_data(self):
        r=self.report();r['assets']['BTC']['timeframes']['4h']['status']='BLOCKED'
        with self.assertRaisesRegex(ValueError,'BTC_REFERENCE'):
            benchmark_overlay(r)
    def test_misaligned_alt_blocks_only_comparison(self):
        r=self.report();r['assets']['ETH']['timeframes']['4h']['identity']='0:240'
        x=benchmark_overlay(r)
        self.assertEqual(x['btc_relative_price_research']['ETH']['status'],'NOT_VALIDATED')
        self.assertEqual(x['totals']['benchmark_comparisons_validated'],9)
    def test_universe_missing_blocks(self):
        r=self.report();del r['assets']['BTC']
        with self.assertRaisesRegex(ValueError,'UNIVERSE'):
            benchmark_overlay(r)
    def test_safety_flags(self):
        r=self.report();r['trading_enabled']=True;r['signals']=[{'asset':'BTC'}]
        x=benchmark_overlay(r)
        self.assertFalse(x['trading_enabled'])
        self.assertFalse(x['signals_enabled'])
        self.assertEqual(x['signals'],[])
        self.assertEqual(x['totals']['trade_authorized'],0)
if __name__=='__main__':unittest.main()
