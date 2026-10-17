import copy
import unittest
from relative_strength_audit_v552 import evaluate

NOW=1800000000
START=(NOW//14400-233)*14400

def fixture():
    times=[START+i*14400 for i in range(233)]
    derived={'generated_at_utc':'2027-01-15T00:00:00+00:00','pairs':{}}
    dual={'generated_at_utc':'2027-01-15T00:00:00+00:00','evaluations':[]}
    market={'generated_at_utc':'2027-01-15T00:00:00+00:00','pairs':{}}
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

class AuditTests(unittest.TestCase):
    def test_ready_without_mutation(self):
        args=fixture();before=copy.deepcopy(args);out=evaluate(*args,NOW)
        self.assertEqual(out['summary']['AUDIT_READY'],4)
        self.assertEqual(out['summary']['scores_modified'],0)
        self.assertEqual(args,before)
    def test_stale_fails_closed(self):
        args=list(fixture());args[0]['generated_at_utc']='2020-01-01T00:00:00+00:00'
        with self.assertRaises(ValueError):evaluate(*args,NOW)
    def test_direct_market_not_overridden(self):
        args=fixture();args[2]['pairs']['AAVEBTC']['frames']['4h']={'status':'available'}
        self.assertEqual(evaluate(*args,NOW)['results']['AAVE']['status'],'AUDIT_BLOCKED')
    def test_gap_blocks(self):
        args=fixture();args[0]['pairs']['AAVEBTC']['frames']['4h']['series'][50]['t']+=1
        self.assertEqual(evaluate(*args,NOW)['results']['AAVE']['status'],'AUDIT_BLOCKED')
    def test_publication_flag_blocks(self):
        args=fixture();args[0]['pairs']['AAVEBTC']['frames']['1h']['publication_eligible']=True
        self.assertEqual(evaluate(*args,NOW)['results']['AAVE']['status'],'AUDIT_BLOCKED')
    def test_no_existing_score_blocks(self):
        args=fixture();args[1]['evaluations'][0]['score']=None
        self.assertEqual(evaluate(*args,NOW)['results']['AAVE']['status'],'AUDIT_BLOCKED')

if __name__=='__main__':unittest.main()
