import unittest
from engine.alpha_screening import screen

class ScreeningTests(unittest.TestCase):
    def template(self):
        x={'version':'alpha-0.2-diagnostic','timeframes':{}}
        for tf in ('5m','15m','1h','4h'):
            x['timeframes'][tf]={'relative_to_btc':{},'native_market_diagnostics':{}}
            for a in ('ETH','BNB','SOL','LTC','LINK','XRP','AVAX','SUI','AAVE','ZEC'):
                x['timeframes'][tf]['relative_to_btc'][a]={'status':'VALIDATED_RELATIVE_CLOSE','identity':'100:5','synthetic_volume':None,'synthetic_liquidity':None,'signals_authorized':False,'relative_close_btc':'0.01'}
                x['timeframes'][tf]['native_market_diagnostics'][a]={'status':'RESEARCH_DIAGNOSTICS_ONLY','identity':'100:5','relative_volume_20':'2','breakout_close_above_resistance':True,'synthetic_volume':None,'volume_is_native':True,'signal_authorized':False,'illustrative_rr_at_least_3':True}
        return x
    def test_no_signals_with_perfect_preliminary_indicators(self):
        r=screen(self.template())
        self.assertEqual(r['totals']['data_valid'],40)
        self.assertEqual(r['totals']['eligible_signals'],0)
        self.assertFalse(r['scores_computed'])
        self.assertIsNone(r['assets']['ETH']['4h']['score'])
    def test_identity_mismatch_blocks(self):
        x=self.template();x['timeframes']['5m']['relative_to_btc']['ETH']['identity']='bad'
        r=screen(x)
        self.assertFalse(r['assets']['ETH']['5m']['data_valid'])
    def test_synthetic_volume_blocks(self):
        x=self.template();x['timeframes']['5m']['relative_to_btc']['ETH']['synthetic_volume']='100'
        r=screen(x)
        self.assertEqual(r['assets']['ETH']['5m']['status'],'BLOCKED')
    def test_zero_volume_does_not_meet_gate(self):
        x=self.template();x['timeframes']['5m']['native_market_diagnostics']['ETH']['relative_volume_20']='0'
        r=screen(x)
        self.assertFalse(r['assets']['ETH']['5m']['rvol_ge_1'])
    def test_no_score_without_policy(self):
        r=screen(self.template())
        self.assertTrue(all(v['score'] is None and not v['signal_authorized']
                            for per in r['assets'].values() for v in per.values()))

if __name__=='__main__': unittest.main()
