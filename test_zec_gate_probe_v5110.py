import unittest
from zec_gate_probe_v5110 import inspect_candles,probe

class ProbeTests(unittest.TestCase):
    def test_empty_history_blocked(self):
        self.assertEqual(inspect_candles([],300,100000)['status'],'BLOCK')
    def test_closed_contiguous_history(self):
        sec=300; now=1000000; start=((now//sec)-250)*sec
        raw=[[str(start+i*sec),'10','0.01','0.02','0.009','0.01','100'] for i in range(250)]
        self.assertEqual(inspect_candles(raw,sec,now)['status'],'PASS_CANDLES_ONLY')
    def test_gap_blocked(self):
        sec=300;now=1000000;start=((now//sec)-250)*sec
        raw=[[str(start+i*sec),'10','0.01','0.02','0.009','0.01','100'] for i in range(250)]
        raw.pop(100)
        self.assertEqual(inspect_candles(raw,sec,now)['reason'],'noncontiguous_history')
    def test_missing_market_fail_closed(self):
        def fetch(path,params=None): raise ValueError('missing market')
        r=probe(fetch,now=1000000)
        self.assertFalse(r['publication_approved']);self.assertFalse(r['gate_fallback_approved'])
        self.assertEqual(r['summary']['closed_candle_frames_passed'],0)
    def test_tradable_does_not_approve(self):
        def fetch(path,params=None):
            if 'currency_pairs' in path:return {'trade_status':'tradable','base':'ZEC','quote':'BTC'}
            if 'tickers' in path:return [{'last':'0.01','quote_volume':'10'}]
            if 'order_book' in path:return {'bids':[['0.01','10']],'asks':[['0.011','10']]}
            return []
        r=probe(fetch,now=1000000)
        self.assertTrue(r['summary']['market_discovered'])
        self.assertFalse(r['summary']['publication_approved'])

if __name__=='__main__':unittest.main()
