import unittest
from decimal import Decimal as D
from unittest.mock import patch
from engine.alpha_belts_v177 import paired_audit,PCT_CAPS

def bar(i,hi='105',lo='95',close='100'):
    return (i*14400,D('100'),D(hi),D(lo),D(close),D('100'))

class PairedBeltTest(unittest.TestCase):
    def test_paired_same_future_and_safety(self):
        bars=[bar(i) for i in range(170)]
        snapshot={'last_close':'100','atr14_simple_research':'3',
          'candidates':[{'type':'resistance','body_level':'102'},
                        {'type':'resistance','body_level':'102.08'},
                        {'type':'resistance','body_level':'104'}]}
        with patch('engine.alpha_belts_v177.extract',return_value=snapshot):
            report=paired_audit(bars,lookback=90,horizon=12,stride=12)
        self.assertEqual(len(report['summaries']),len(PCT_CAPS))
        self.assertTrue(all(r['past_last_epoch']<r['decision_epoch'] for r in report['observations']))
        for key,v in report['summaries'].items():
            self.assertEqual(v['paired_belt_occurrences'],v['both_rejection']+
                v['belt_only_rejection']+v['component_only_rejection']+
                sum(1 for r in report['observations'] for p in r['variants'][key]
                    if p['belt_outcome']!='REJECTION_CLOSE' and not p['any_component_rejection']))
        self.assertEqual(report['signals'],[])
        for k in ('signals_enabled','trading_enabled','trade_authorized',
                  'backtest_completed','release_6_0_0_approved'):
            self.assertFalse(report[k])
    def test_bad_history(self):
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT'):
            paired_audit([bar(i) for i in range(60)])
        broken=[bar(i) for i in range(160)]
        broken[25]=bar(26)
        with self.assertRaisesRegex(ValueError,'NONCONTIGUOUS'):
            paired_audit(broken)
if __name__=='__main__':unittest.main()
