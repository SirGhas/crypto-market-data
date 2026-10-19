import unittest
from engine.alpha_swing_run_v163 import observed_ticker, attach_prices
from engine.alpha_swing_run_v162 import UNIVERSE

class TestSpotTicker(unittest.TestCase):
    def payload(self,ts=1000000,inst='BTC-USDT',price='100'):
        return {'code':'0','data':[{'instId':inst,'last':price,'bidPx':'99','askPx':'101','ts':str(ts)}]}
    def test_valid_timestamped_spot_observation(self):
        x=observed_ticker('BTC',transport=lambda u:self.payload(),now_ms=1002000)
        self.assertEqual(x['last_trade_price'],'100')
        self.assertEqual(x['timestamp_age_ms'],2000)
    def test_stale_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'STALE'):
            observed_ticker('BTC',transport=lambda u:self.payload(),now_ms=1040000)
    def test_wrong_symbol_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'SYMBOL'):
            observed_ticker('ETH',transport=lambda u:self.payload(),now_ms=1000000)
    def test_invalid_price_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'PRICE'):
            observed_ticker('BTC',transport=lambda u:self.payload(price='0'),now_ms=1000000)
    def test_all_11_reported_even_if_unavailable(self):
        report={'version':'alpha-1.6.2-btc-benchmark-research','assets':{a:{} for a in UNIVERSE},'totals':{},'signals':[]}
        x=attach_prices(report,{'BTC':{'status':'OBSERVED','last_trade_price':'100'}})
        self.assertEqual(len(x['observed_spot_prices']),11)
        self.assertEqual(x['totals']['observed_spot_prices'],1)
        self.assertFalse(x['trading_enabled'])
        self.assertEqual(x['signals'],[])
if __name__=='__main__':unittest.main()
