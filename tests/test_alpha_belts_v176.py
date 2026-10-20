import unittest
from decimal import Decimal as D
from unittest.mock import patch
from engine.alpha_belts_v176 import evaluate,outcome,PCT_CAPS

def b(i,hi='104',lo='96',cl='100'):
    return (i*14400,D('100'),D(hi),D(lo),D(cl),D('100'))

class HistoricalBelts(unittest.TestCase):
    def test_resistance_close_through(self):
        self.assertEqual(outcome('resistance',D('102'),D('103'),[b(0,'105','99','104')]),'CLOSE_THROUGH')
    def test_support_rejection(self):
        x=[b(0,'104','98','100'),b(1,'106','100','105'),b(2,'106','102','104')]
        self.assertEqual(outcome('support',D('98'),D('99'),x),'REJECTION_CLOSE')
    def test_no_touch(self):
        self.assertEqual(outcome('resistance',D('110'),D('111'),[b(i) for i in range(4)]),'NO_TOUCH')
    def test_historical_independence_and_safety(self):
        bars=[b(i) for i in range(150)]
        snapshot={'last_close':'100','atr14_simple_research':'2','candidates':[
            {'type':'resistance','body_level':'103'},
            {'type':'resistance','body_level':'103.08'},
            {'type':'resistance','body_level':'106'}]}
        with patch('engine.alpha_belts_v176.extract',return_value=snapshot):
            data=evaluate(bars,lookback=90,horizon=12,stride=12)
        self.assertEqual(len(data['results']),len(PCT_CAPS))
        self.assertTrue(all(r['last_historical_epoch']<r['decision_epoch'] for r in data['observations']))
        self.assertFalse(data['signals_enabled'])
        self.assertFalse(data['trade_authorized'])
        self.assertFalse(data['backtest_completed'])
        self.assertEqual(data['signals'],[])
    def test_noncontiguous_guard(self):
        bars=[b(i) for i in range(150)]
        bars[40]=b(50)
        with self.assertRaisesRegex(ValueError,'NONCONTIGUOUS'):
            evaluate(bars)
if __name__=='__main__':unittest.main()
