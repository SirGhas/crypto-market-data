import unittest
from decimal import Decimal as D
from engine.alpha_flip_v172 import observe_flip,walkforward_flip

def bar(i,high='101',low='99',close='100'):
    return (i*14400,D('100'),D(high),D(low),D(close),D('100'))

class TestFlip(unittest.TestCase):
    def test_successful_flip(self):
        x=[bar(i) for i in range(8)]
        x[0]=bar(0,'105','99','103')
        x[1]=bar(1,'105','101','103')
        x[2]=bar(2,'104','100.2','101')
        x[3]=bar(3,'103','100.5','102')
        x[4]=bar(4,'105','101','104')
        self.assertEqual(observe_flip(D('100'),D('10'),x)['outcome'],'SUCCESSFUL_FLIP')
    def test_failed_breakout(self):
        x=[bar(i) for i in range(8)]
        x[0]=bar(0,'105','99','103')
        self.assertEqual(observe_flip(D('100'),D('10'),x)['outcome'],'FAILED_BREAKOUT')
    def test_no_breakout(self):
        self.assertEqual(observe_flip(D('120'),D('10'),[bar(i) for i in range(8)])['outcome'],'NO_CONFIRMED_BREAKOUT')
    def test_no_future_mislabeled_as_success(self):
        x=[bar(i) for i in range(4)]
        x[0]=bar(0,'105','99','103');x[1]=bar(1,'105','101','103')
        x[3]=bar(3,'104','100','102')
        self.assertEqual(observe_flip(D('100'),D('10'),x)['outcome'],'RETEST_UNRESOLVED')
    def test_history_insufficient(self):
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT'):
            walkforward_flip([bar(i) for i in range(110)])
if __name__=='__main__':unittest.main()
