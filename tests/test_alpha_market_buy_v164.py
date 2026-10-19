import unittest
from engine.alpha_market_buy_v164 import assess,overlay,UNIVERSE

def market(ask='100',resistance='104',stop='94'):
    return {'observed_spot_price_v163':{
        'status':'OBSERVED','symbol':'BTC-USDT','best_ask':ask,'best_bid':'99',
        'last_trade_price':'99.5','observed_timestamp_ms':100000,'observed_at_utc':'test'},
        'risk_v15':{'hypothetical_stop':stop,
                     'nearest_overhead_resistance':resistance,
                     'data_validation':{'matched_report_candle_identities':True}},
        'resistance_gate_v151':{'first_four_hour_resistance':resistance},
        'evidence_v161':{'order_book':{'status':'OBSERVED',
                       'snapshots':[{'observed_timestamp_ms':99900}]}}}
class Tests(unittest.TestCase):
    def test_cost_rr_below_gross(self):
        x=assess('BTC',market())
        self.assertEqual(x['status'],'SCENARIO_COMPUTED_NOT_EXECUTION_VALIDATED')
        self.assertLess(float(x['scenario_net_rr_after_assumed_costs']),
                        float(x['gross_rr_from_ask']))
        self.assertFalse(x['trade_authorized'])
    def test_stale_resistance_below_ask_blocks(self):
        x=assess('BTC',market(ask='105',resistance='104'))
        self.assertIsNone(x['scenario_net_rr_after_assumed_costs'])
        self.assertIn('NO_VERIFIED_RESISTANCE_ABOVE_OBSERVED_ASK',x['blocking_reasons'])
    def test_invalid_stop_blocks(self):
        x=assess('BTC',market(stop='101'))
        self.assertIsNone(x['scenario_net_rr_after_assumed_costs'])
    def test_missing_book_fails_closed(self):
        m=market();m['evidence_v161']['order_book']['status']='UNAVAILABLE'
        x=assess('BTC',m)
        self.assertIn('ORDER_BOOK_NOT_VALIDATED',x['blocking_reasons'])
        self.assertFalse(x['trade_authorized'])
    def test_all_assets_research_only(self):
        raw={'version':'alpha-1.6.3-observed-spot-prices',
             'assets':{a:{} for a in UNIVERSE},'totals':{},'signals':[1],
             'trading_enabled':True}
        x=overlay(raw)
        self.assertEqual(len(x['market_buy_research']),11)
        self.assertEqual(x['signals'],[])
        self.assertFalse(x['trading_enabled'])
        self.assertEqual(x['totals']['market_buy_execution_validated'],0)
if __name__=='__main__':unittest.main()
