import unittest
from decimal import Decimal as D
from unittest.mock import patch
from engine.alpha_flip_v174 import replay,PARAMETERS,HORIZONS,GAPS
from engine.alpha_flip_v173 import observe_flip_v173

def candle(i):
    return (i*14400,D('100'),D('104'),D('99'),D('102'),D('100'))

class CombinedResearchTests(unittest.TestCase):
    def test_variant_matrix_and_paired_counts(self):
        bars=[candle(i) for i in range(220)]
        snapshot={'atr14_simple_research':'10','last_close':'100'}
        candidates=[(D('80'),D('112'),{}),(D('30'),D('109'),{})]
        with patch('engine.alpha_flip_v174.extract',return_value=snapshot),patch(
            'engine.alpha_flip_v174.rank_candidates',return_value=candidates):
            report=replay(bars,lookback=90,stride=24)
        self.assertEqual(len(report['summaries']),len(PARAMETERS)*len(HORIZONS))
        self.assertGreater(report['evaluations'],0)
        sample=report['summaries']['baseline_18']
        self.assertEqual(sample['ranked']['evaluations'],report['evaluations'])
        self.assertEqual(sample['distance_matched']['0.5']['distinct_comparable_pairs'],report['evaluations'])
        for row in report['events']:
            if row['status']=='EVALUATED':
                self.assertLess(row['historical_last_closed_epoch'],row['decision_epoch'])
        for name in ('signals_enabled','trading_enabled','trade_authorized','backtest_completed',
                     'continuous_freshness_proven','release_6_0_0_approved'):
            self.assertFalse(report[name])
        self.assertEqual(report['signals'],[])
    def test_grid_dimensions_and_guards(self):
        self.assertEqual(len(PARAMETERS)*len(HORIZONS)*len(GAPS),27)
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT'):
            replay([candle(i) for i in range(50)])
        with self.assertRaisesRegex(ValueError,'NONCONTIGUOUS'):
            bars=[candle(i) for i in range(180)]
            bars[120]=(bars[120][0]+10,)+bars[120][1:]
            replay(bars)
    def test_close_not_wick_and_failed_retest(self):
        future=[candle(i) for i in range(6)]
        future[0]=(0,D('100'),D('110'),D('99'),D('104'),D('100'))
        future[1]=(14400,D('104'),D('110'),D('101'),D('103'),D('100'))
        future[2]=(28800,D('103'),D('105'),D('100'),D('102'),D('100'))
        future[3]=(43200,D('102'),D('120'),D('101'),D('103'),D('100'))
        future[4]=(57600,D('103'),D('120'),D('101'),D('103'),D('100'))
        self.assertEqual(observe_flip_v173(D('100'),D('10'),future)['outcome'],
                         'RETEST_NO_CONFIRMED_CONTINUATION')
if __name__=='__main__':unittest.main()
