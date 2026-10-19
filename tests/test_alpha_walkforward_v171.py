import unittest
from decimal import Decimal as D
from engine.alpha_walkforward_v171 import classify,walkforward
def make(n=120):
    return [(i*14400,D('100'),D('102'),D('98'),D('100'),D('100')) for i in range(n)]
class TestWalkForward(unittest.TestCase):
    def test_no_touch(self):
        self.assertEqual(classify(D('110'),D('5'),make(6)),'NO_TOUCH')
    def test_breakout(self):
        x=make(6);x[0]=(0,D('100'),D('112'),D('99'),D('111'),D('100'))
        self.assertEqual(classify(D('110'),D('5'),x),'BREAKOUT_CLOSE')
    def test_confirmed_rejection(self):
        x=make(6);x[0]=(0,D('100'),D('111'),D('99'),D('100'),D('100'))
        x[1]=(14400,D('100'),D('101'),D('107'),D('100'),D('100')) # synthetic classification low intentionally decisive
        self.assertEqual(classify(D('110'),D('5'),x),'REJECTION_OBSERVED')
    def test_history_insufficient(self):
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT'):
            walkforward(make(80))
    def test_future_timeline_strict(self):
        rows=make(120);rows[95]=(95*14400+1,D('100'),D('102'),D('98'),D('100'),D('100'))
        with self.assertRaisesRegex(ValueError,'NON_CONTIGUOUS'):
            walkforward(rows)
if __name__=='__main__':unittest.main()
