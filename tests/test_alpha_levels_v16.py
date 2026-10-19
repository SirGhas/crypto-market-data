import unittest
from decimal import Decimal as D
from engine.alpha_levels_v16 import pivots,cluster,quality,inspect_asset,overlay

class TestLevels(unittest.TestCase):
    def make_rows(self,step,n=70):
        rows=[]
        for i in range(n):
            # Recurring, separated local highs/lows with a mild trend.
            c=D(100)+D(i%9-4)*D('0.4')
            rows.append((i*step,D(100),c+D('1.1'),c-D('1.1'),D(100)))
        return rows
    def market(self):
        rows4=self.make_rows(14400);rowsD=self.make_rows(86400)
        return {'timeframes':{
            '4h':{'status':'VALIDATED','identity':str(rows4[-1][0])+':240','close':'100'},
            '1D':{'status':'VALIDATED','identity':str(rowsD[-1][0])+':1440','close':'100'}}},rows4,rowsD
    def test_confirmed_pivots_not_last_two(self):
        rows=self.make_rows(14400)
        p=pivots(rows,'4h')
        self.assertTrue(p)
        self.assertTrue(all(x['epoch']<=rows[-3][0] for x in p))
    def test_cluster_separates_sides(self):
        p=[{'timeframe':'4h','side':'support','price':D('95'),'epoch':1},
           {'timeframe':'1D','side':'support','price':D('95.2'),'epoch':2},
           {'timeframe':'4h','side':'resistance','price':D('95.1'),'epoch':3}]
        g=cluster(p,D('.5'))
        self.assertEqual(len(g),2)
        self.assertEqual(len([v for v in g if v['side']=='support'][0]['points']),2)
    def test_daily_has_greater_base_weight(self):
        x={'side':'resistance','points':[{'timeframe':'1D','price':D(105),'epoch':100}]}
        y={'side':'resistance','points':[{'timeframe':'4h','price':D(105),'epoch':100}]}
        self.assertGreater(quality(x,100)['partial_score_out_of_100'],quality(y,100)['partial_score_out_of_100'])
    def test_partial_evidence_not_full_quality(self):
        g={'points':[{'timeframe':'1D','price':D(105),'epoch':100}]}
        q=quality(g,100)
        self.assertEqual(q['evidence_cap'],70)
        self.assertIn('PARTIAL',q['evidence_quality'])
    def test_valid_reports_with_mock_history(self):
        m,a,b=self.market()
        def get(_,bar):return a if bar=='4H' else b
        z=inspect_asset('TEST',m,get)
        self.assertEqual(z['status'],'PARTIAL_LEVEL_QUALITY_RESEARCH')
        self.assertTrue(z['data_validation']['candle_identities_matched'])
        self.assertFalse(z['trade_authorized'])
        self.assertGreater(len(z['zones']),0)
    def test_candle_mismatch_failclosed(self):
        m,a,b=self.market();m['timeframes']['4h']['close']='101'
        z=inspect_asset('TEST',m,lambda _,bar:a if bar=='4H' else b)
        self.assertEqual(z['status'],'BLOCKED_UNVERIFIED_LEVEL_QUALITY')
        self.assertIn('REPORT_CLOSE_MISMATCH_4h',z['blocking_reasons'])
    def test_no_network_on_invalid_report(self):
        m,_,_=self.market();m['timeframes']['1D']['status']='MISSING'
        z=inspect_asset('X',m,lambda *_:self.fail('called network'))
        self.assertFalse(z['trade_authorized'])
        self.assertEqual(z['zones'],[])
    def test_overlay_failclosed(self):
        m,a,b=self.market()
        r=overlay({'version':'alpha-1.5.1-resistance-gates-research','assets':{'X':m}},lambda _,bar:a if bar=='4H' else b)
        self.assertFalse(r['signals_enabled'])
        self.assertEqual(r['signals'],[])
        self.assertEqual(r['totals']['trade_authorized'],0)
        self.assertEqual(r['totals']['level_quality_partial'],1)
    def test_reject_wrong_version(self):
        with self.assertRaises(ValueError):overlay({'version':'other','assets':{}})

if __name__=='__main__':unittest.main()
