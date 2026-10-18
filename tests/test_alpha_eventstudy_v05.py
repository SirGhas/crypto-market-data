import unittest
from decimal import Decimal
from engine.alpha_eventstudy_v05 import event_study

def make(n=399):
    base=300*(6000000//300)
    r={}
    for i in range(n):
        x=Decimal(100)
        r[base+300*i]={'start_epoch':base+300*i,'open':x,'high':x+1,'low':x-1,'close':x,'base_volume':Decimal(10)}
    return r,base
class EventStudyTest(unittest.TestCase):
    def test_normal_flat_no_events(self):
        rows,start=make()
        s=event_study(rows,'5m',start+len(rows)*300)
        self.assertEqual(s['status'],'RESEARCH_EVENT_STUDY_VALID')
        self.assertEqual(len(s['events']),0)
        self.assertFalse(s['backtest_completed'])
    def test_breakout_forward_only(self):
        rows,start=make()
        key=start+250*300
        rows[key]['close']=Decimal(105);rows[key]['high']=Decimal(106)
        rows[key]['base_volume']=Decimal(25)
        # Event results derive from later bars, not the event bar.
        s=event_study(rows,'5m',start+len(rows)*300)
        self.assertEqual(s['counts']['breakout'],1)
        e=s['events'][0]
        self.assertEqual(e['candle_id'],f'{key}:5')
        self.assertLess(Decimal(e['forward']['1']['raw_return_pct']),0)
    def test_gap_fail_closed(self):
        rows,start=make();del rows[start+180*300]
        self.assertEqual(event_study(rows,'5m',start+399*300)['reason'],'NONCONTIGUOUS_HISTORY')
    def test_short_history_blocks(self):
        rows,start=make(244)
        self.assertEqual(event_study(rows,'5m',start+244*300)['status'],'BLOCKED')
    def test_last_closed_required(self):
        rows,start=make();del rows[start+398*300]
        self.assertEqual(event_study(rows,'5m',start+399*300)['reason'],'LATEST_CLOSED_CANDLE_UNAVAILABLE')
if __name__=='__main__':unittest.main()
