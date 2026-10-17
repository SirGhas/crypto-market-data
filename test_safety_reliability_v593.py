import copy
import datetime as dt
import unittest
from safety_reliability_v593 import evaluate, positive_checks
NOW=1800000000
STAMP=dt.datetime.fromtimestamp(NOW,dt.timezone.utc).isoformat()
def sample():
    e={'coin':'AVAX','score':60,'relative_volume_1h':1.4,'relative_volume_4h':1.4,'risk_reward_validated_levels':4,
       'static_levels':{'support':9,'resistance':12,'support_touches':2,'resistance_touches':2}}
    dual={'generated_at_utc':STAMP,'evaluations':[e]}
    guard={'generated_at_utc':STAMP,'coins':{'AVAX':{'positive_publication_gate':'PASS'}}}
    lifecycle={'generated_at_utc':STAMP,'new_publishable_events':[]}
    outbox={'pending':{},'delivered_ids':[]}
    return dual,guard,lifecycle,outbox
class Tests(unittest.TestCase):
    def test_clean_no_mutation(self):
        a=sample();original=copy.deepcopy(a)
        r=evaluate(*a,NOW)
        self.assertEqual(r['coins']['AVAX']['status'],'ADDITIONAL_CHECKS_PASS')
        self.assertEqual(a,original)
    def test_weak_avax_volume_blocks(self):
        a=list(sample());a[0]['evaluations'][0].update(relative_volume_1h=.784,relative_volume_4h=.438)
        self.assertIn('4h_volume_not_confirmed',evaluate(*a,NOW)['coins']['AVAX']['reasons'])
    def test_low_rr_blocks(self):
        e=sample()[0]['evaluations'][0];e['risk_reward_validated_levels']=2.5
        self.assertIn('rr_below_3_or_unverified',positive_checks(e))
    def test_forming_event_blocks(self):
        e=sample()[0]['evaluations'][0]
        event={'event_type':'approaching_resistance','status':'forming_watch','volume_confirmed_4h':True,'lower_tf_confirmed':True,'closed_4h_at_utc':STAMP}
        self.assertIn('forming_or_unconfirmed_event',positive_checks(e,event))
    def test_valid_event_passes(self):
        e=sample()[0]['evaluations'][0]
        event={'event_type':'4h_closed_breakout','status':'technical_event_needs_context','volume_confirmed_4h':True,'lower_tf_confirmed':True,'closed_4h_at_utc':STAMP}
        self.assertEqual(positive_checks(e,event),[])
    def test_stale_fails(self):
        a=list(sample());a[1]['generated_at_utc']='2020-01-01T00:00:00+00:00'
        self.assertEqual(evaluate(*a,NOW)['status'],'BLOCK')
    def test_duplicate_queue_collision_fails(self):
        a=list(sample());a[3]['pending']={'x':{'status':'PENDING_DELIVERY','event':{'id':'x'}}};a[3]['delivered_ids']=['x']
        self.assertEqual(evaluate(*a,NOW)['status'],'BLOCK')
    def test_original_block_not_promoted(self):
        a=list(sample());a[1]['coins']['AVAX']['positive_publication_gate']='BLOCK'
        self.assertEqual(evaluate(*a,NOW)['coins']['AVAX']['status'],'BLOCK')
    def test_no_event_transport(self):
        r=evaluate(*sample(),NOW)
        self.assertEqual(r['summary']['sent'],0)
        self.assertFalse(r['release_6_0_0_approved'])
if __name__=='__main__':unittest.main()
