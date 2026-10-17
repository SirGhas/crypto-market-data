import copy
import datetime as dt
import unittest
from preflight_v590 import evaluate
NOW=1800000000
STAMP=dt.datetime.fromtimestamp(NOW,dt.timezone.utc).isoformat()
COINS=('AAVE','AVAX','LINK','SUI')
def fixture():
    candidate={'generated_at_utc':STAMP,'coins':{c:{'status':'CANDIDATE_READY','old_score':55,'candidate_score':60,'old_gate':'BLOCK','hypothetical_guard':'BLOCK','effective_publication':'BLOCK'} for c in COINS}}
    dual={'generated_at_utc':STAMP,'evaluations':[{'coin':c,'score':55,'tier':'below_threshold_watch_only'} for c in COINS]}
    guard={'generated_at_utc':STAMP,'coins':{c:{'positive_publication_gate':'BLOCK'} for c in COINS}}
    outbox={'pending':{},'delivered_ids':[]}
    lifecycle={'generated_at_utc':STAMP,'new_publishable_events':[]}
    return [candidate,dual,guard,outbox,lifecycle]
class PreflightTests(unittest.TestCase):
    def test_clean_dry_run(self):
        args=fixture();original=copy.deepcopy(args)
        self.assertEqual(evaluate(*args,NOW)['status'],'PASS_DRY_RUN')
        self.assertEqual(args,original)
    def test_divergence_review_not_failure(self):
        a=fixture();a[0]['coins']['AVAX'].update(status='BLOCK',hypothetical_guard='PASS')
        r=evaluate(*a,NOW);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertEqual(r['gate_divergences'],1)
    def test_unblocked_divergence_fails(self):
        a=fixture();a[0]['coins']['AVAX']['hypothetical_guard']='PASS'
        self.assertEqual(evaluate(*a,NOW)['status'],'BLOCK')
    def test_unblocked_publication_fails(self):
        a=fixture();a[0]['coins']['AVAX']['effective_publication']='PASS'
        self.assertEqual(evaluate(*a,NOW)['status'],'BLOCK')
    def test_stale_fails(self):
        a=fixture();a[2]['generated_at_utc']='2020-01-01T00:00:00+00:00'
        self.assertEqual(evaluate(*a,NOW)['status'],'BLOCK')
    def test_pending_delivered_collision_fails(self):
        a=fixture();a[3]['pending']={'a':{'status':'PENDING_DELIVERY','event':{'id':'a'}}};a[3]['delivered_ids']=['a']
        self.assertEqual(evaluate(*a,NOW)['status'],'BLOCK')
    def test_invalid_pending_record_fails(self):
        a=fixture();a[3]['pending']={'a':{'status':'DELIVERED','event':{'id':'a'}}}
        self.assertEqual(evaluate(*a,NOW)['status'],'BLOCK')
if __name__=='__main__':unittest.main()
