import unittest
from price_parity_guard_v547 import assess, suppress, FRAMES

NOW = 1792176000

def sample(gate_multiplier=1.0, gate_source='Gate.io Spot'):
    pairs = {}
    for tf, seconds in FRAMES.items():
        start = (NOW // seconds - 233) * seconds
        def frame(price, source):
            candles = [{'t': start + i * seconds, 'c': price, 'v': 10.0} for i in range(233)]
            return {'status': 'available', 'source': source, 'candles': candles}
        for coin in ('BNB', 'XRP'):
            pairs.setdefault(coin+'BTC', {'frames': {}})['frames'][tf] = frame(0.01*gate_multiplier, gate_source)
            pairs.setdefault(coin+'USDT', {'frames': {}})['frames'][tf] = frame(1000, 'OKX Spot')
        pairs.setdefault('BTCUSDT', {'frames': {}})['frames'][tf] = frame(100000, 'OKX Spot')
    return {'pairs': pairs}

class PriceParityTests(unittest.TestCase):
    def test_aligned_price_passes(self):
        self.assertEqual(assess(sample(), 'XRP', NOW)['status'], 'PASS')
    def test_deviation_blocks(self):
        self.assertEqual(assess(sample(1.04), 'BNB', NOW)['status'], 'BLOCK')
    def test_wrong_source_blocks(self):
        self.assertEqual(assess(sample(gate_source='OKX Spot'), 'XRP', NOW)['status'], 'BLOCK')
    def test_stale_blocks(self):
        self.assertEqual(assess(sample(), 'BNB', NOW+15000)['status'], 'BLOCK')
    def test_missing_cross_blocks(self):
        m = sample(); del m['pairs']['XRPBTC']
        self.assertEqual(assess(m, 'XRP', NOW)['status'], 'BLOCK')
    def test_suppression_preserves_score_and_bearish(self):
        x={'coin':'XRP','tier':'tier_1_priority_watch','score':82,'score_components':{'volume':25}}
        dual={'evaluations':[x],'tier_1_top_three':[x.copy()],'tier_2_top_three':[],'summary':{}}
        events={'new_events':[{'id':'up','coin':'XRP','event_type':'4h_closed_breakout'}, {'id':'down','coin':'XRP','event_type':'4h_closed_breakdown'}], 'summary':{}}
        report={'evaluations':[],'top_three_watchlist':[]}
        signals={'evaluations':[],'new_events':[],'summary':{}}
        suppress('XRP',dual,events,report,signals,{})
        self.assertEqual(x['score'],82)
        self.assertEqual(x['score_components'],{'volume':25})
        self.assertEqual(dual['tier_1_top_three'],[])
        self.assertEqual([e['id'] for e in events['new_events']],['down'])

if __name__=='__main__': unittest.main()
