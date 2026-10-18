import unittest,copy
from engine.alpha_integrity_v08 import compare_runs,event_statistics,check_reports

def item(identity='100:5',v='5'):
    return {'status':'RESEARCH_VALIDATED','sma_close':{'identity':identity,'smas':{'SMA233':{'value':v}}},
            'rsi14':{'identity':identity,'value':'55'},
            'native_volume_price_action':{'identity':identity,'rvol20':'1.5'},
            'event_study':{'events':[]}}

def report(run,time,ident='100:5',v='5'):
    return {'version':'alpha-0.6-rsi-volume','run_id':run,'timestamp_utc':time,'timeframes':{'5m':{'LTC':item(ident,v)}}}

class TestV08(unittest.TestCase):
    def test_advanced(self):
        p=report('1','2026-10-18T11:00:00+00:00','100:5')
        q=report('2','2026-10-18T11:10:00+00:00','400:5')
        x=compare_runs(p,q);self.assertEqual(x['status'],'ADVANCED_SAMPLE_CONFIRMED');self.assertFalse(x['proof'])
    def test_same_bar_unchanged(self):
        p=report('1','2026-10-18T11:00:00+00:00')
        q=report('2','2026-10-18T11:01:00+00:00')
        self.assertEqual(compare_runs(p,q)['status'],'NO_ADVANCE_YET')
    def test_same_bar_changed(self):
        p=report('1','2026-10-18T11:00:00+00:00')
        q=report('2','2026-10-18T11:01:00+00:00',v='6')
        self.assertEqual(compare_runs(p,q)['status'],'ANOMALY_DETECTED')
    def test_no_prior(self):self.assertEqual(compare_runs(None,report('1','2026-10-18T11:00:00+00:00'))['status'],'NO_PREVIOUS_BASELINE')
    def test_embargo(self):
        e=lambda t: {'candle_id':f'{t}:5','direction':'breakout','above_sma233':True,'sma233_slope':'UP',
                     'forward':{x:{'direction_aligned_pct':'1'} for x in ('1','3','6','12')}}
        m={'timeframes':{'5m':{'LTC':{'event_study':{'events':[e(300),e(600),e(4200),e(4500),e(8100)]}}}}}
        x=event_statistics(m)
        self.assertEqual(x['events_embargo_selected'],3)
    def test_run_mismatch(self):
        with self.assertRaises(ValueError):check_reports({'source_version':'alpha-0.6-rsi-volume','source_run_id':'1','source_time_utc':'t','research_only':True,'signals_enabled':False,'trading_enabled':False,'totals':{'graded':40}},
        {'version':'alpha-0.6-rsi-volume','run_id':'2','timestamp_utc':'t','research_only':True,'signals_enabled':False,'trading_enabled':False,'totals':{'validated':40}})
if __name__=='__main__':unittest.main()
