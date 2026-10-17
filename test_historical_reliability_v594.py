import copy,datetime as dt,unittest
from historical_reliability_v594 import reasons_view,replay_delivery,historical_volume_audit,evaluate
NOW=1800000000
STAMP=dt.datetime.fromtimestamp(NOW,dt.timezone.utc).isoformat()
def fixture():
    cs=[]
    for i in range(60):cs.append({'t':NOW-60*3600+i*3600,'o':10,'h':11,'l':9,'c':10,'v':10 if i<59 else 20})
    four=[dict(c,t=NOW-60*14400+i*14400) for i,c in enumerate(cs)]
    market={'generated_at_utc':STAMP,'pairs':{'AAVEUSDT':{'frames':{'1h':{'status':'available','candles':cs},'4h':{'status':'available','candles':four}}}}}
    dual={'generated_at_utc':STAMP,'evaluations':[{'coin':'AAVE','score':70,'relative_volume_1h':.8,'relative_volume_4h':1.5,'risk_reward_validated_levels':4,'static_levels':{'support':8,'resistance':12,'support_touches':2,'resistance_touches':2}}]}
    guard={'generated_at_utc':STAMP,'coins':{'AAVE':{'positive_publication_gate':'PASS'}}}
    lifecycle={'generated_at_utc':STAMP,'new_publishable_events':[]}
    outbox={'pending':{},'delivered_ids':[]}
    return market,dual,guard,lifecycle,outbox
class Tests(unittest.TestCase):
    def test_primary_priority(self):self.assertEqual(reasons_view(['rr_below_3_or_unverified','missing_or_stale_market_data'])['primary_rejection_reason'],'missing_or_stale_market_data')
    def test_secondary_preserved(self):self.assertEqual(len(reasons_view(['volume_1h_below_candidate_threshold','rr_below_3_or_unverified'])['all_reasons']),2)
    def test_fresh_replay_dedup(self):
        e=[{'id':'x','eligible':True,'confirmed':True}];a=replay_delivery(e);b=replay_delivery(e,a['pending_ids']);self.assertEqual(b['results'][0]['status'],'DUPLICATE_SUPPRESSED')
    def test_unconfirmed_rejected(self):self.assertEqual(replay_delivery([{'id':'x','eligible':True,'confirmed':False}])['results'][0]['status'],'BLOCK')
    def test_pending_preserved(self):self.assertEqual(replay_delivery([],['x'])['pending_ids'],['x'])
    def test_historical_no_future_volume(self):
        m=fixture()[0];a=historical_volume_audit(m);self.assertEqual(a['AAVE']['1h']['passing_observations'],1)
    def test_gap_unverified(self):
        m=fixture()[0];m['pairs']['AAVEUSDT']['frames']['1h']['candles'][35]['t']+=1;self.assertEqual(historical_volume_audit(m)['AAVE']['1h']['status'],'UNVERIFIED')
    def test_no_mutation(self):
        a=fixture();b=copy.deepcopy(a);evaluate(*a,NOW);self.assertEqual(a,b)
    def test_volume_rejection_reason(self):self.assertEqual(evaluate(*fixture(),NOW)['coins']['AAVE']['primary_rejection_reason'],'volume_1h_below_candidate_threshold')
    def test_stale_fails_closed(self):
        a=list(fixture());a[2]['generated_at_utc']='2020-01-01T00:00:00+00:00';self.assertEqual(evaluate(*a,NOW)['status'],'BLOCK')
    def test_queue_collision_fails(self):
        a=list(fixture());a[4]['pending']={'x':{}};a[4]['delivered_ids']=['x'];self.assertEqual(evaluate(*a,NOW)['status'],'BLOCK')
    def test_no_release_or_send(self):
        r=evaluate(*fixture(),NOW);self.assertFalse(r['release_6_0_0_approved']);self.assertEqual(r['summary']['sent'],0)
if __name__=='__main__':unittest.main()
