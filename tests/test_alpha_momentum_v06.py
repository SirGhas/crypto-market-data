import unittest
from decimal import Decimal
from engine.alpha_momentum_v06 import rsi_wilder,volume_price_action

def make_rows(closes,period=300):
    output={}
    for i,c in enumerate(closes):
        d=Decimal(str(c));output[i*period]={'open':d,'close':d,'high':d+1,'low':d-1,'base_volume':Decimal(10)}
    return output

class Tests(unittest.TestCase):
    def test_constant_rsi_50(self):
        rows=make_rows([100]*100)
        val=rsi_wilder(rows,'5m',30000)
        self.assertEqual(val['status'],'RSI_WILDER_CLOSE_VALIDATED')
        self.assertEqual(Decimal(val['value']),50)
    def test_up_rsi_100(self):
        rows=make_rows(range(100,200))
        self.assertEqual(Decimal(rsi_wilder(rows,'5m',30000)['value']),100)
    def test_down_rsi_zero(self):
        rows=make_rows(range(200,100,-1))
        self.assertEqual(Decimal(rsi_wilder(rows,'5m',30000)['value']),0)
    def test_gap_blocks(self):
        rows=make_rows(range(100,200));del rows[300]
        self.assertEqual(rsi_wilder(rows,'5m',30000)['status'],'BLOCKED')
    def test_vol_native(self):
        rows=make_rows([100]*100);rows[99*300]['base_volume']=Decimal(20)
        out=volume_price_action(rows,'5m',30000)
        self.assertEqual(Decimal(out['rvol20']),2)
        self.assertTrue(out['rvol_ge_2'])
        self.assertFalse(out['signals_authorized'])
    def test_mismatched_count_blocks(self):
        rows=make_rows([100]*10)
        self.assertEqual(volume_price_action(rows,'5m',30000)['status'],'BLOCKED')
if __name__=='__main__':unittest.main()
