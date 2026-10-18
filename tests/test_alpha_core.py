import unittest
from decimal import Decimal
from engine.alpha_core import parse_okx_rows,relative_close,InvalidMarketData

class AlphaCoreTests(unittest.TestCase):
    def row(self,t,close='100',confirm='1'):
        return [str(t*1000),'100','220','90',close,'8','800','800',confirm]
    def test_ratio(self):
        t=1800
        a=parse_okx_rows({'code':'0','data':[self.row(t,'100')]},'5m',2100)
        b=parse_okx_rows({'code':'0','data':[self.row(t,'200')]},'5m',2100)
        x=relative_close(a,b,'5m',2100)
        self.assertEqual(x['relative_close_btc'],'0.500000000000')
        self.assertIsNone(x['synthetic_volume'])
        self.assertFalse(x['signals_authorized'])
    def test_forming_excluded(self):
        a=parse_okx_rows({'code':'0','data':[self.row(2100,'100','0')]},'5m',2200)
        self.assertEqual(a,{})
    def test_stale_blocks(self):
        t=1500
        a=parse_okx_rows({'code':'0','data':[self.row(t)]},'5m',2100)
        self.assertEqual(relative_close(a,a,'5m',2100)['status'],'BLOCKED')
    def test_malformed_block(self):
        with self.assertRaises(InvalidMarketData): parse_okx_rows({'code':'51000','data':[]},'5m',2100)
    def test_nonpositive_excluded(self):
        self.assertEqual(parse_okx_rows({'code':'0','data':[self.row(1800,'0')]},'5m',2100),{})
    def test_unaligned_excluded(self):
        self.assertEqual(parse_okx_rows({'code':'0','data':[self.row(1801)]},'5m',2101),{})
    def test_unchanged_price_new_candle_is_valid(self):
        a=parse_okx_rows({'code':'0','data':[self.row(1800,'100')]},'5m',2100)
        self.assertEqual(relative_close(a,a,'5m',2100)['status'],'VALIDATED_RELATIVE_CLOSE')
    def test_duplicate_conflicting_blocks(self):
        with self.assertRaises(InvalidMarketData): parse_okx_rows({'code':'0','data':[self.row(1800,'100'),self.row(1800,'101')]},'5m',2100)

if __name__=='__main__':unittest.main()
