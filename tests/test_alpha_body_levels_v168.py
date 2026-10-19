import unittest
from decimal import Decimal as D
from engine.alpha_body_levels_v168 import extract,parse

class TestBodyLevels(unittest.TestCase):
    def bars(self):
        b=[]
        for i in range(65):
            o=D('100');c=D('99') if i%3==0 else D('101')
            b.append((i*14400,o,D('110'),D('90'),c,D('100')))
        return b
    def test_wicks_not_body_pivots(self):
        a=extract('4h',self.bars())
        self.assertTrue(all(D(x['body_level'])<=D('101') for x in a['candidates'] if x['type']=='resistance'))
    def test_nonclosed_candle_rejected(self):
        r=[[(i*14400)*1000,'100','105','95','101','10','0','0','1'] for i in range(65)]
        r[-1][8]='0'
        self.assertEqual(len(parse(r,'4h',65*14400)),64)
    def test_no_trade_authorization_of_candidates(self):
        self.assertEqual(extract('4h',self.bars())['status'],'BODY_LEVEL_RESEARCH')
    def test_gapped_history_rejected(self):
        r=[[(i*14400)*1000,'100','105','95','101','10','0','0','1'] for i in range(65) if i!=35]
        with self.assertRaisesRegex(ValueError,'GAPPED'):
            parse(r,'4h',65*14400)
if __name__=='__main__':unittest.main()
