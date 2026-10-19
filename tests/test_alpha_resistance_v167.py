import unittest
from decimal import Decimal as D
from engine.alpha_resistance_v167 import evaluate_zone

def sample():
    x=[]
    for i in range(50):x.append([i*14400,D('98'),D('99'),D('97'),D('98'),D('100')])
    return x
class Test(unittest.TestCase):
    def test_genuine_approach_and_downward_rejection(self):
        rows=sample()
        rows[30]=[30*14400,D('99'),D('101'),D('98'),D('98.5'),D('200')]
        rows[31]=[31*14400,D('98.5'),D('99'),D('94'),D('95'),D('150')]
        r=evaluate_zone({'low':'100','high':'100'},rows,D('10'),'4h')
        self.assertEqual(r['event_count'],1)
        self.assertFalse(r['events'][0]['volume_is_at_level'])
    def test_no_down_candle_no_rejection(self):
        rows=sample();rows[30]=[30*14400,D('98'),D('101'),D('97'),D('99'),D('200')]
        self.assertEqual(evaluate_zone({'low':'100','high':'100'},rows,D('10'),'4h')['event_count'],0)
    def test_bar_from_above_is_not_upward_test(self):
        rows=sample();rows[29]=[29*14400,D('102'),D('103'),D('101'),D('102'),D('100')]
        rows[30]=[30*14400,D('101'),D('101.5'),D('98'),D('99'),D('200')]
        self.assertEqual(evaluate_zone({'low':'100','high':'100'},rows,D('10'),'4h')['event_count'],0)
    def test_next_candles_must_confirm(self):
        rows=sample();rows[30]=[30*14400,D('99'),D('101'),D('98'),D('98.5'),D('200')]
        rows[31]=[31*14400,D('99'),D('101'),D('98'),D('100.5'),D('150')]
        rows[32]=[32*14400,D('100'),D('102'),D('98'),D('100.5'),D('100')]
        self.assertEqual(evaluate_zone({'low':'100','high':'100'},rows,D('10'),'4h')['event_count'],0)
    def test_inadequate_reaction_not_confirmed(self):
        rows=sample();rows[30]=[30*14400,D('99'),D('101'),D('98'),D('98.5'),D('200')]
        rows[31]=[31*14400,D('98'),D('99'),D('98'),D('98.5'),D('100')]
        rows[32]=[32*14400,D('98'),D('99'),D('98'),D('98.5'),D('100')]
        self.assertEqual(evaluate_zone({'low':'100','high':'100'},rows,D('10'),'4h')['event_count'],0)
if __name__=='__main__':unittest.main()
