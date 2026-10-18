import unittest
from copy import deepcopy
from decimal import Decimal as D
from engine.alpha_swing_v12 import tf_condition,score_watch,snapshot,TFS

def audit(tf,stamp=100000):
    return {'status':'VALIDATED','identity':f'{stamp}:{tf}','last_closed_start_epoch':stamp,
        'close':'105','rsi14':'55','rvol20':'1.6','broke_resistance_20':False,'broke_support_20':False,
        'static_levels':{'20':{'support':'95','resistance':'110'}},
        'sma_close':{'SMA233':{'value':'100','previous':'99','slope':'UP','close_above':True,'close_below':False},
          'SMA20':{'value':'102'},'SMA50':{'value':'101'}}}

def markets():return {tf:{'ETH':audit(tf)} for tf in TFS}

class V12(unittest.TestCase):
    def test_weights(self):
        s=score_watch({tf:audit(tf) for tf in TFS});self.assertEqual(s['early_score'],'80');self.assertEqual(s['alignment_score'],'80')
        self.assertEqual(sum(s['weights'].values()),100)
    def test_15m_less_than_30m(self):
        a={tf:audit(tf) for tf in TFS};a['15m']['rsi14']='49';r1=score_watch(a)
        a['15m']['rsi14']='55';a['30m']['rsi14']='49';r2=score_watch(a)
        self.assertGreater(D(r1['early_score']),D(r2['early_score']))
    def test_missing_blocks(self):
        a={tf:audit(tf) for tf in TFS};a['30m']={'status':'BLOCKED'}
        self.assertEqual(score_watch(a)['status'],'BLOCKED')
    def test_research_only(self):
        r=snapshot(markets(),100000)
        self.assertEqual(r['signals'],[]);self.assertFalse(r['trading_enabled']);self.assertEqual(r['totals']['expected_timeframes'],6)
    def test_no_duplicate(self):
        m=markets();prior=snapshot(m,100000);new=snapshot(m,100000,prior)
        self.assertEqual(new['watch_events'],[]);self.assertEqual(new['cross_run']['unchanged'],6)
    def test_early_change_not_requires_4h(self):
        m=markets();prior=snapshot(m,100000);m2=deepcopy(m);m2['15m']['ETH']['last_closed_start_epoch']+=900
        m2['15m']['ETH']['identity']='100900:15m';m2['15m']['ETH']['rsi14']='45';m2['15m']['ETH']['rvol20']='0.3'
        result=snapshot(m2,101000,prior)
        self.assertEqual(result['cross_run']['advanced'],1)
        self.assertTrue(any(e['type']=='EARLY_CHANGE' for e in result['watch_events']))
    def test_regression_blocks(self):
        m=markets();old=snapshot(m,100000);m['15m']['ETH']['last_closed_start_epoch']=99999
        r=snapshot(m,100001,old);self.assertEqual(r['cross_run']['status'],'ANOMALIES')
    def test_revision_blocks(self):
        m=markets();old=snapshot(m,100000);m['15m']['ETH']['close']='105.5'
        r=snapshot(m,100001,old);self.assertEqual(r['watch_events'],[]);self.assertTrue(r['cross_run']['anomalies'])
if __name__=='__main__':unittest.main()
