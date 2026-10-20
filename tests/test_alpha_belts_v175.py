import unittest
from decimal import Decimal as D
from engine.alpha_belts_v175 import build_belts,assemble
def z(side,p,tf='15m'):return {'side':side,'price':D(str(p)),'timeframe':tf}
class BeltResearchTests(unittest.TestCase):
    def test_narrow_belt_and_centers(self):
        r=build_belts([z('resistance',100),z('resistance',100.05,'4h'),
          z('resistance',101),z('support',98),z('support',97)],D('100'),D('1'))
        self.assertEqual(len(r['belts']),1)
        b=r['belts'][0]
        self.assertEqual(b['lower_bound'],'100')
        self.assertEqual(b['upper_bound'],'100.05')
        self.assertEqual(b['geometric_center'],'100.025')
        self.assertEqual(b['structural_tier'],'INTERMEDIATE')
    def test_relative_price_cap_rejects_25_percent_zone(self):
        r=build_belts([z('resistance',8),z('resistance',10),z('resistance',11)],D('8'),D('1'))
        self.assertEqual(r['belts'],[])
    def test_chain_must_not_make_wide_belt(self):
        levels=[z('resistance',x) for x in ('100','100.1','100.2','100.3','101')]
        r=build_belts(levels,D('100'),D('10'))
        self.assertTrue(all(D(b['width_pct'])<=D('.2') for b in r['belts']))
    def test_external_gap_is_required(self):
        r=build_belts([z('support',99),z('support',99.05)],D('100'),D('1'))
        self.assertEqual(r['belts'],[])
        self.assertEqual(len(r['unmerged_levels']),2)
    def test_structure_gap_gate(self):
        r=build_belts([z('support',99),z('support',99.1),z('support',99.3)],
                      D('100'),D('1'))
        self.assertEqual(r['belts'],[])
    def test_invalid_reference_and_caps(self):
        with self.assertRaises(ValueError):build_belts([],D('0'),D('1'))
        with self.assertRaises(ValueError):build_belts([],D('100'),D('1'),pct_cap=D('2'))
    def test_assemble_safety_and_source(self):
        tfs={k:{'candidates':[],'last_close':'100','atr14_simple_research':'1'}
             for k in ('15m','30m','1h','2h','4h','1D')}
        tfs['15m']['candidates']=[{'type':'resistance','body_level':'100.02'}]
        tfs['4h']['candidates']=[{'type':'resistance','body_level':'100.03'}]
        tfs['1D']['candidates']=[{'type':'resistance','body_level':'101.00'}]
        r=assemble({'asset':'BTC','primary_timeframe':'4h','timeframes':tfs})
        self.assertEqual(r['candidate_levels'],3)
        self.assertEqual(len(r['belts']),1)
        self.assertEqual(r['belts'][0]['structural_tier'],'INTERMEDIATE')
        for k in ('signals_enabled','trading_enabled','trade_authorized','backtest_completed',
                  'continuous_freshness_proven','release_6_0_0_approved'):
            self.assertIs(r[k],False)
        self.assertEqual(r['signals'],[])
if __name__=='__main__':unittest.main()
