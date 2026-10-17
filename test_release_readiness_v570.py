import copy
import datetime as dt
import unittest
from release_readiness_v570 import evaluate

NOW=1800000000
STAMP=dt.datetime.fromtimestamp(NOW,dt.timezone.utc).isoformat()
COINS=('AAVE','AVAX','LINK','SUI')

def fixture():
    integration={'generated_at_utc':STAMP,'summary':{'PASS':4,'BLOCK':0,'live_scores_modified':0,'publication_gates_modified':0,'direct_feeds_upgraded':0},'coins':{}}
    shadow={'generated_at_utc':STAMP,'summary':{'SHADOW_READY':4,'SHADOW_BLOCKED':0,'live_scores_modified':0,'publication_gates_modified':0,'direct_feeds_upgraded':0},'coins':{}}
    derived={'generated_at_utc':STAMP,'pairs':{}}
    market={'generated_at_utc':STAMP,'pairs':{}}
    guard={'generated_at_utc':STAMP,'coins':{}}
    health={'generated_at_utc':STAMP,'freshness':{'summary':{'STALE':0,'UNVERIFIED':16}}}
    for coin in COINS:
        integration['coins'][coin]={'status':'PASS','original_publication_gate':'BLOCK'}
        shadow['coins'][coin]={'status':'SHADOW_READY','original_publication_gate':'BLOCK','shadow_publication_gate':'NOT_EVALUATED_NEVER_AUTHORIZE','delta':5}
        derived['pairs'][coin+'BTC']={'frames':{tf:{'status':'DERIVED_READY','publication_eligible':False,'direct_btc_market_verified':False} for tf in ('5m','15m','1h','4h')}}
        market['pairs'][coin+'BTC']={'frames':{}}
        guard['coins'][coin]={'positive_publication_gate':'BLOCK'}
    return [integration,shadow,derived,market,guard,health]

class ReadinessTests(unittest.TestCase):
    def test_valid_shadow_passes_but_not_release(self):
        args=fixture();original=copy.deepcopy(args);r=evaluate(*args,NOW)
        self.assertEqual(r['status'],'PASS_SHADOW_ONLY');self.assertFalse(r['release_6_0_0_approved']);self.assertEqual(args,original)
    def test_stale_blocks(self):
        args=fixture();args[0]['generated_at_utc']='2020-01-01T00:00:00+00:00';self.assertEqual(evaluate(*args,NOW)['status'],'BLOCK')
    def test_unexpected_score_mutation_blocks(self):
        args=fixture();args[1]['summary']['live_scores_modified']=1;self.assertEqual(evaluate(*args,NOW)['status'],'BLOCK')
    def test_fake_direct_market_blocks(self):
        args=fixture();args[3]['pairs']['AAVEBTC']['frames']['4h']={'status':'available'};self.assertEqual(evaluate(*args,NOW)['status'],'BLOCK')
    def test_derived_publication_flag_blocks(self):
        args=fixture();args[2]['pairs']['AAVEBTC']['frames']['4h']['publication_eligible']=True;self.assertEqual(evaluate(*args,NOW)['status'],'BLOCK')
    def test_guard_mismatch_blocks(self):
        args=fixture();args[4]['coins']['AAVE']['positive_publication_gate']='PASS';self.assertEqual(evaluate(*args,NOW)['status'],'BLOCK')
    def test_stale_feed_blocks(self):
        args=fixture();args[5]['freshness']['summary']['STALE']=1;self.assertEqual(evaluate(*args,NOW)['status'],'BLOCK')

if __name__=='__main__':unittest.main()
