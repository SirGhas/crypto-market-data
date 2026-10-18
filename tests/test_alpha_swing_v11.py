import unittest
from decimal import Decimal as D
from engine.alpha_core import BARS
from engine.alpha_swing_v11 import inspect,score_setup,early_warning,build_report
BARS.update({'2h':(7200,'2H'),'1D':(86400,'1Dutc')})
def samples(tf):
    sec=BARS[tf][0];now=500*sec
    rows={}
    for i in range(400):
        t=(100+i)*sec;cl=D('100')+D(i)/20
        rows[t]={'open':cl-D('0.1'),'high':cl+D('0.25'),'low':cl-D('0.25'),
                 'close':cl,'base_volume':D('100')}
    return inspect(rows,tf,now)
class TestSwing(unittest.TestCase):
    def test_indicators(self):
        for tf in ('1h','2h','4h','1D'):
            self.assertEqual(samples(tf)['status'],'VALIDATED')
    def test_research_only(self):
        audits={tf:{'ETH':samples(tf)} for tf in ('1h','2h','4h','1D')}
        r=build_report(audits,500*14400)
        self.assertFalse(r['trading_enabled']);self.assertEqual(r['signals'],[])
        self.assertEqual(r['totals']['reference_graded'],1)
        self.assertTrue(r['assets']['ETH']['early_score']['independent_of_4h_score'])
    def test_gap_blocks(self):
        self.assertEqual(inspect({},'4h',500*14400)['status'],'BLOCKED')
    def test_repeat_dedup(self):
        audits={tf:{'ETH':samples(tf)} for tf in ('1h','2h','4h','1D')}
        r=build_report(audits,500*14400)
        r2=build_report(audits,500*14400,r)
        self.assertEqual(r2['notifications'],[])
    def test_daily_required(self):
        p=samples('4h');self.assertEqual(score_setup(p,{'status':'BLOCKED'},{},{})['status'],'BLOCKED')
if __name__=='__main__':unittest.main()
