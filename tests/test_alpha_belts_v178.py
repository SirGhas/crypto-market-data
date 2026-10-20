import unittest
from decimal import Decimal as D
from unittest.mock import patch
from engine.alpha_belts_v178 import observe_zone,audit

def bar(i,high='104',low='96',close='100'):
    return (i*14400,D('100'),D(high),D(low),D(close),D('100'))

class BoundaryAuditTests(unittest.TestCase):
    def test_rejection_and_breakout_require_two_subsequent_closes(self):
        r=[bar(0,'104','99','102'),bar(1,'102','97','99'),bar(2,'101','96','98')]
        self.assertEqual(observe_zone('resistance',D('100'),D('101'),r),'CONFIRMED_REJECTION')
        b=[bar(0,'104','99','102'),bar(1,'106','102','104'),bar(2,'108','102','105')]
        self.assertEqual(observe_zone('resistance',D('100'),D('101'),b),'CONFIRMED_CLOSE_THROUGH')
    def test_wicks_alone_not_confirmed(self):
        a=[bar(0,'107','98','100'),bar(1,'106','98','100.5'),bar(2,'104','98','100.5')]
        self.assertEqual(observe_zone('resistance',D('100'),D('101'),a),'TOUCH_AMBIGUOUS')
    def test_window_right_censored(self):
        self.assertEqual(observe_zone('resistance',D('100'),D('101'),[bar(0)]),'TOUCH_UNRESOLVED')
    def test_support_and_validation(self):
        x=[bar(0,'103','97','98'),bar(1,'105','100','102'),bar(2,'105','100','103')]
        self.assertEqual(observe_zone('support',D('98'),D('99'),x),'CONFIRMED_REJECTION')
        with self.assertRaises(ValueError):observe_zone('support',D('102'),D('101'),x)
        with self.assertRaises(ValueError):observe_zone('unknown',D('99'),D('100'),x)
    def test_safe_paired_audit(self):
        bars=[bar(i) for i in range(170)]
        snapshot={'last_close':'100','atr14_simple_research':'3','candidates':[
          {'type':'resistance','body_level':'102'},
          {'type':'resistance','body_level':'102.08'},
          {'type':'resistance','body_level':'104'}]}
        with patch('engine.alpha_belts_v178.extract',return_value=snapshot):
            report=audit(bars)
        self.assertGreater(report['evaluations'],0)
        self.assertTrue(all(r['past_last_epoch']<r['decision_epoch'] for r in report['observations']))
        self.assertFalse(report['signals_enabled'])
        self.assertFalse(report['trade_authorized'])
        self.assertEqual(report['signals'],[])
if __name__=='__main__':unittest.main()
