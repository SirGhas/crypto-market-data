import unittest
from engine.alpha_importance_v179 import build_map,classify,score_level

class ImportanceTests(unittest.TestCase):
    def test_tiers(self):
        self.assertEqual(classify('15m'),'MINOR')
        self.assertEqual(classify('4h'),'INTERMEDIATE')
        self.assertEqual(classify('4h',['2h']),'MAJOR')
        self.assertEqual(classify('1D'),'MAJOR')
        self.assertEqual(classify('4h',['15m']),'INTERMEDIATE')
    def test_scores_bounded_and_not_probabilities(self):
        self.assertLessEqual(score_level('1D',100,100),100)
        self.assertGreater(score_level('1D',1,0),score_level('15m',1,0))
    def test_map_safety_and_provenance(self):
        tfs={k:{'last_close':'100','atr14_simple_research':'2','candidates':[]}
          for k in ('15m','30m','1h','2h','4h','1D')}
        tfs['15m']['candidates']=[{'type':'resistance','body_level':'102',
          'body_pivot_count':1,'confirmed_approach_rejections':1}]
        tfs['4h']['candidates']=[{'type':'resistance','body_level':'102.08',
          'body_pivot_count':2,'confirmed_approach_rejections':1}]
        tfs['1D']['candidates']=[{'type':'resistance','body_level':'103',
          'body_pivot_count':2,'confirmed_approach_rejections':1}]
        result=build_map({'asset':'BTC','primary_timeframe':'4h','timeframes':tfs})
        self.assertEqual(result['candidate_levels'],3)
        self.assertEqual(len(result['belts']),1)
        self.assertEqual(result['belts'][0]['structural_tier'],'INTERMEDIATE')
        self.assertEqual(result['signals'],[])
        for key in ('signals_enabled','trading_enabled','trade_authorized',
                    'backtest_completed','continuous_freshness_proven','release_6_0_0_approved'):
            self.assertFalse(result[key])
    def test_bad_probe(self):
        with self.assertRaises(ValueError):
            build_map({'asset':'ETH','primary_timeframe':'4h'})
if __name__=='__main__':unittest.main()
