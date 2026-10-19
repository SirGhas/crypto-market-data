import unittest
from engine.alpha_depth_v165 import sweep,fetch_book,evaluate,overlay

class DepthTests(unittest.TestCase):
    def test_sweep_full_two_levels(self):
        x=sweep([['100','5'],['101','10']], '1000')
        self.assertEqual(x['status'],'FULLY_COVERED_BY_OBSERVED_ASK_DEPTH')
        self.assertEqual(x['levels_consumed'],2)
        self.assertGreater(float(x['vwap']),100)
    def test_partial_depth_blocks(self):
        x=sweep([['100','1'],['101','1']], '1000')
        self.assertEqual(x['status'],'INSUFFICIENT_OBSERVED_DEPTH')
        self.assertIsNone(x['vwap'])
    def test_bad_level_order_rejected(self):
        with self.assertRaisesRegex(ValueError,'ASCENDING'):
            sweep([['101','1'],['100','1']], '150')
    def test_book_freshness(self):
        row={'code':'0','data':[{'ts':'100000','bids':[['99','10']], 'asks':[['100','10']]}]}
        b=fetch_book('BTC',transport=lambda url:row,now_ms=101000)
        self.assertEqual(b['status'],'OBSERVED')
        self.assertEqual(b['ask_level_count'],1)
        with self.assertRaisesRegex(ValueError,'STALE'):
            fetch_book('BTC',transport=lambda url:row,now_ms=110000)
    def test_no_trade_auth_on_depth(self):
        m={'observed_spot_price_v163':{'status':'OBSERVED','symbol':'BTC-USDT',
           'best_ask':'100','observed_timestamp_ms':101000},
           'risk_v15':{'hypothetical_stop':'90',
              'data_validation':{'matched_report_candle_identities':True}},
           'market_buy_v164':{'nearest_resistance_above_ask':'130'}}
        b={'status':'OBSERVED','symbol':'BTC-USDT','best_ask':'100','age_ms':1000,
           'observed_timestamp_ms':101000,'ask_levels':[['100','5'],['101','10']]}
        x=evaluate('BTC',m,b)
        self.assertEqual(x['status'],'DEPTH_SCENARIO_COMPUTED_NOT_EXECUTION_VALIDATED')
        self.assertIsNotNone(x['net_rr_after_depth_and_assumed_costs'])
        self.assertFalse(x['trade_authorized'])
    def test_mismatched_book_ticker_blocks(self):
        m={'observed_spot_price_v163':{'status':'OBSERVED','symbol':'BTC-USDT',
           'best_ask':'100','observed_timestamp_ms':200000}}
        b={'status':'OBSERVED','symbol':'BTC-USDT','best_ask':'100','age_ms':500,
           'observed_timestamp_ms':150000,'ask_levels':[['100','20']]}
        self.assertEqual(evaluate('BTC',m,b)['status'],'BLOCKED_DEPTH_RESEARCH')

if __name__=='__main__':unittest.main()
