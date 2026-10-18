import unittest
from copy import deepcopy
from engine.alpha_alerts_v13 import classify

TFS=('15m','30m','1h','2h','4h','1D')
def mock(score_old=20,score_new=34,break_support=False,vol='2'):
    def bars(t):
        return {x:{'status':'VALIDATED','identity':f'{t}:{x}','last_closed_start_epoch':t,
                   'broke_support_20':break_support if x=='15m' else False,
                   'candle_direction':'DOWN' if x=='15m' else 'UP',
                   'rvol20':vol,'close':'10'} for x in TFS}
    prev={'version':'alpha-1.2-multi-timeframe-watch','assets':{'BTC':{'timeframes':bars(1),'watch_score':{'early_score':score_old},'reference_score':{'tier':'GRAY'}}}}
    current={'version':'alpha-1.2-multi-timeframe-watch','assets':{'BTC':{'timeframes':bars(2),'watch_score':{'early_score':score_new},'reference_score':{'tier':'GRAY'}}},
             'cross_run':{'status':'COMPARED','advanced':6,'unchanged':0,'anomalies':[]},'totals':{}}
    return prev,current

class TestClassifier(unittest.TestCase):
    def test_small_score_no_spam(self):
        a,b=mock(score_new=22)
        self.assertEqual(classify(a,b)['research_alerts'],[])
    def test_early_research_alert(self):
        a,b=mock()
        alerts=classify(a,b)['research_alerts']
        self.assertEqual(len(alerts),1)
        self.assertEqual(alerts[0]['type'],'EARLY_STRENGTHENING')
    def test_support_break_is_risk_independent_score(self):
        a,b=mock(score_new=20,break_support=True)
        self.assertEqual(classify(a,b)['research_alerts'][0]['direction'],'RISK_DOWN')
    def test_no_risk_without_high_volume(self):
        a,b=mock(score_new=20,break_support=True,vol='1.1')
        self.assertEqual(classify(a,b)['research_alerts'],[])
    def test_event_dedup(self):
        a,b=mock(break_support=True)
        x=classify(a,b)
        a2=deepcopy(a);a2['alert_history']=x['alert_history']
        self.assertEqual(classify(a2,b)['research_alerts'],[])
    def test_anomaly_blocks(self):
        a,b=mock();b['cross_run']['anomalies']=[{'reason':'SAME_CANDLE_REVISION'}]
        self.assertEqual(classify(a,b)['research_alerts'],[])
    def test_no_previous(self):
        _,b=mock();self.assertEqual(classify(None,b)['research_alerts'],[])
if __name__=='__main__':unittest.main()
