import copy
import unittest
NOW=1800000000
START=(NOW//14400-233)*14400

def fixture():
    times=[START+i*14400 for i in range(233)]
    derived={'pairs':{}}
    dual={'evaluations':[]}
    market={'pairs':{}}
    for coin in ('AAVE','AVAX','LINK','SUI'):
        frames={tf:{'status':'DERIVED_READY','publication_eligible':False,'direct_btc_market_verified':False} for tf in ('5m','15m','1h','4h')}
        frames['4h'].update(series=[{'t':t,'relative_close':1+i/1000} for i,t in enumerate(times)],last_candle_id=str(times[-1]))
        derived['pairs'][coin+'BTC']={'frames':frames}
        dual['evaluations'].append({'coin':coin,'score':65,'tier':'below_threshold_watch_only','relative_strength_btc':None,'score_components':{'relative_btc':0}})
        market['pairs'][coin+'BTC']={'frames':{}}
    import datetime as dt
    stamp=dt.datetime.fromtimestamp(NOW,dt.timezone.utc).isoformat()
    for doc in (derived,dual,market):doc['generated_at_utc']=stamp
    return derived,dual,market
from shadow_relative_screen_v553 import evaluate, tier
import datetime as dt

class ShadowTests(unittest.TestCase):
    def inputs(self):
        derived,dual,market=fixture()
        guard={'generated_at_utc':dt.datetime.fromtimestamp(NOW,dt.timezone.utc).isoformat(),'coins':{}}
        for e in dual['evaluations']:
            e['weights']={'relative_btc':5}
            e['score_components']={'relative_btc':0,'volume':15,'static_levels':20,'trend_4h':15,'risk_reward':15}
            e['risk_reward_validated_levels']=3
            guard['coins'][e['coin']]={'score':65,'original_tier':e['tier'],'positive_publication_gate':'BLOCK'}
        return derived,dual,market,guard
    def test_shadow_does_not_mutate(self):
        args=self.inputs(); before=copy.deepcopy(args)
        r=evaluate(*args,NOW)
        self.assertEqual(r['summary']['SHADOW_READY'],4)
        self.assertEqual(r['summary']['publication_gates_modified'],0)
        self.assertEqual(args,before)
        self.assertEqual(r['coins']['AAVE']['shadow_score'],70)
        self.assertEqual(r['coins']['AAVE']['original_publication_gate'],'BLOCK')
    def test_stale_guard_blocks(self):
        args=self.inputs();args[3]['generated_at_utc']='2020-01-01T00:00:00+00:00'
        with self.assertRaises(ValueError): evaluate(*args,NOW)
    def test_mismatched_guard_blocks(self):
        args=self.inputs();args[3]['coins']['AAVE']['score']=70
        self.assertEqual(evaluate(*args,NOW)['coins']['AAVE']['status'],'SHADOW_BLOCKED')
    def test_weight_change_blocks(self):
        args=self.inputs();args[1]['evaluations'][0]['weights']['relative_btc']=10
        self.assertEqual(evaluate(*args,NOW)['coins']['AAVE']['status'],'SHADOW_BLOCKED')
    def test_derived_not_ready_blocks(self):
        args=self.inputs();args[0]['pairs']['AAVEBTC']['frames']['4h']['status']='DERIVED_BLOCKED'
        self.assertEqual(evaluate(*args,NOW)['coins']['AAVE']['status'],'SHADOW_BLOCKED')
    def test_rr_gate(self):
        self.assertEqual(tier(80,{'static_levels':30,'volume':25},None),'below_threshold_watch_only')
        self.assertEqual(tier(80,{'static_levels':30,'volume':25},3),'tier_1_priority_watch')
if __name__=='__main__':unittest.main()
