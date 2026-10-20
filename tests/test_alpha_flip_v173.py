import unittest
from decimal import Decimal as D
from engine.alpha_flip_v173 import observe_flip_v173,walkforward_flip_v173

def bar(i, high='103', low='101', close='102'):
    return (i*14400,D('102'),D(high),D(low),D(close),D('100'))

class StrictFlipTest(unittest.TestCase):
    def sample(self):
        x=[bar(i) for i in range(8)]
        x[0]=bar(0,'105','99','103')
        x[1]=bar(1,'105','101','103')
        x[2]=bar(2,'104','100','102')
        x[3]=bar(3,'106','101','105')
        x[4]=bar(4,'107','102','106')
        return x
    def test_close_confirmed_flip(self):
        self.assertEqual(observe_flip_v173(D('100'),D('10'),self.sample())['outcome'],'SUCCESSFUL_FLIP')
    def test_wick_only_bounce_not_success(self):
        x=self.sample()
        x[3]=bar(3,'110','101','103')
        x[4]=bar(4,'111','101','103')
        self.assertEqual(observe_flip_v173(D('100'),D('10'),x)['outcome'],'RETEST_NO_CONFIRMED_CONTINUATION')
    def test_retest_below_level_fails(self):
        x=self.sample()
        x[2]=bar(2,'102','99','99.5')
        self.assertEqual(observe_flip_v173(D('100'),D('10'),x)['outcome'],'FAILED_RETEST')
    def test_deep_wick_ambiguous(self):
        x=self.sample()
        x[2]=bar(2,'104','97','102')
        self.assertEqual(observe_flip_v173(D('100'),D('10'),x)['outcome'],'AMBIGUOUS_RETEST')
    def test_final_retest_is_unresolved(self):
        x=self.sample()[:3]
        self.assertEqual(observe_flip_v173(D('100'),D('10'),x)['outcome'],'RETEST_UNRESOLVED')
    def test_no_breakout(self):
        self.assertEqual(observe_flip_v173(D('120'),D('10'),[bar(i) for i in range(5)])['outcome'],'NO_CONFIRMED_BREAKOUT')
    def test_failed_stabilization(self):
        x=self.sample()
        x[1]=bar(1,'104','98','99')
        self.assertEqual(observe_flip_v173(D('100'),D('10'),x)['outcome'],'FAILED_BREAKOUT')
    def test_bad_atr(self):
        with self.assertRaises(ValueError):
            observe_flip_v173(D('100'),D('0'),self.sample())
    def test_insufficient_history(self):
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT'):
            walkforward_flip_v173([bar(i) for i in range(110)])

if __name__=='__main__': unittest.main()
