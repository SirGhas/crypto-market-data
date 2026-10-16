"""Offline regression checks. Run: python -m unittest test_gate_integration_v545.py"""
import unittest
from unittest.mock import patch
import multisource_collector as m

class ControlledGateTests(unittest.TestCase):
    def test_approved_pairs_only(self):
        self.assertEqual(m.GATE_APPROVED,{'BNBBTC','XRPBTC'})
        with self.assertRaisesRegex(ValueError,'not_approved'):
            m.gate('SUIBTC','4h')
    def test_gate_mapping_and_volume(self):
        sample=[["1792152000","0.00003","0.008903","0.009","0.0088","0.0089","2.321"]]
        with patch.object(m,'get',return_value=sample) as mocked:
            row=m.gate('BNBBTC','4h')[0]
            self.assertEqual(row,{'t':1792152000,'o':0.0089,'h':0.009,'l':0.0088,'c':0.008903,'v':2.321})
            self.assertIn('BNB_BTC',mocked.call_args.args[0])
    def test_contiguous_valid_candles(self):
        sec=14400; now=1792179000; start=now-234*sec
        candles=[{'t':start+i*sec,'o':1.,'h':1.,'l':1.,'c':1.,'v':1.} for i in range(233)]
        # Construct a fully closed, fresh last candle.
        start=(now//sec-233)*sec
        candles=[dict(c,t=start+i*sec) for i,c in enumerate(candles)]
        self.assertEqual(len(m.validate(candles,'4h',now)),233)
        candles[-2]['t']+=1
        with self.assertRaisesRegex(ValueError,'gap'):
            m.validate(candles,'4h',now)

if __name__=='__main__': unittest.main()
