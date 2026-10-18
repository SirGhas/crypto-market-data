import unittest
from zec_feed_audit_v5100 import inspect, FRAMES

NOW=1_800_000_000

def market(source='OKX Spot',bad_tf=None):
    pairs={}
    for symbol in ('ZECUSDT','ZECBTC'):
        frames={}
        for tf,seconds in FRAMES.items():
            last=(NOW//seconds-1)*seconds
            candles=[{'t':last-(232-i)*seconds,'o':'1','h':'2','l':'0.5','c':'1.5','v':'10'} for i in range(233)]
            frames[tf]={'status':'available','source':source,'candles':candles}
        pairs[symbol]={'frames':frames}
    if bad_tf: pairs['ZECBTC']['frames'][bad_tf]['candles'][-1]['t']+=1
    return {'pairs':pairs}

class Tests(unittest.TestCase):
    def test_all_eight(self):
        r=inspect(market(),NOW);self.assertEqual(r['summary']['attempted_feeds'],8);self.assertEqual(r['summary']['passed_feeds'],8)
        self.assertFalse(r['summary']['publication_approved'])
    def test_fallback_blocked(self):
        r=inspect(market('Bybit Spot'),NOW);self.assertEqual(r['summary']['blocked_feeds'],8)
    def test_gap_blocked(self):
        r=inspect(market(bad_tf='4h'),NOW);self.assertIn('noncontiguous_candles',r['feeds']['ZECBTC']['4h']['errors'])
    def test_no_false_staleness_same_boundary(self):
        r=inspect(market(),NOW);second=inspect(market(),NOW+10,r)
        self.assertEqual(second['summary']['passed_feeds'],8)
        self.assertFalse(second['summary']['cross_run_advance_proven'])
    def test_missing_cross(self):
        m=market();del m['pairs']['ZECBTC'];r=inspect(m,NOW);self.assertEqual(r['summary']['blocked_feeds'],4)
    def test_regression(self):
        m=market();r=inspect(m,NOW);r['feeds']['ZECBTC']['4h']['last_closed_end_unix']+=14400
        s=inspect(m,NOW,r);self.assertIn('candle_regression',s['feeds']['ZECBTC']['4h']['errors'])

if __name__=='__main__':unittest.main()
