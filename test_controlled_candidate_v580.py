import copy
import datetime as dt
import unittest
from unittest.mock import patch
from test_shadow_relative_screen_v553 import ShadowTests, NOW
from controlled_candidate_v580 import inspect

STAMP=dt.datetime.fromtimestamp(NOW,dt.timezone.utc).isoformat()

def fixture():
    derived,dual,market,guard=ShadowTests().inputs()
    liquidity={'generated_at_utc':STAMP,'status':'BLOCK'}
    parity={'generated_at_utc':STAMP,'pairs':{}}
    lifecycle={'generated_at_utc':STAMP,'new_publishable_events':[]}
    outbox={'pending':{},'delivered_ids':[]}
    return [derived,dual,market,guard,liquidity,parity,lifecycle,outbox]

def mock_guard(market,dual,liquidity,parity,now):
    return {'coins':{e['coin']:{'positive_publication_gate':'BLOCK','reason_codes':['not_a_qualified_candidate']} for e in dual['evaluations']}}

class CandidateTests(unittest.TestCase):
    @patch('controlled_candidate_v580.guard_evaluate',side_effect=mock_guard)
    def test_ready_no_mutation(self,_):
        args=fixture();before=copy.deepcopy(args);r=inspect(*args,NOW)
        self.assertEqual(r['summary']['CANDIDATE_READY'],4)
        self.assertEqual(r['summary']['live_scores_modified'],0)
        self.assertEqual(args,before)
        self.assertFalse(r['release_6_0_0_approved'])
        self.assertTrue(all(v['effective_publication']=='BLOCK' for v in r['coins'].values()))
    @patch('controlled_candidate_v580.guard_evaluate',side_effect=mock_guard)
    def test_stale_blocks(self,_):
        args=fixture();args[4]['generated_at_utc']='2020-01-01T00:00:00+00:00'
        with self.assertRaises(ValueError):inspect(*args,NOW)
    @patch('controlled_candidate_v580.guard_evaluate',side_effect=mock_guard)
    def test_score_mismatch_blocks(self,_):
        args=fixture();args[3]['coins']['AAVE']['score']=999
        self.assertEqual(inspect(*args,NOW)['coins']['AAVE']['status'],'BLOCK')
    @patch('controlled_candidate_v580.guard_evaluate',side_effect=mock_guard)
    def test_invalid_outbox_blocks(self,_):
        args=fixture();args[7]={'pending':[],'delivered_ids':[]}
        with self.assertRaises(ValueError):inspect(*args,NOW)
    @patch('controlled_candidate_v580.guard_evaluate')
    def test_gate_divergence_blocks(self,g):
        args=fixture();g.side_effect=lambda *a:{'coins':{e['coin']:{'positive_publication_gate':'PASS','reason_codes':[]} for e in a[1]['evaluations']}}
        r=inspect(*args,NOW)
        self.assertEqual(r['summary']['gate_divergences'],4)
        self.assertEqual(r['summary']['BLOCK'],4)
    @patch('controlled_candidate_v580.guard_evaluate',side_effect=mock_guard)
    def test_missing_derived_blocks(self,_):
        args=fixture();args[0]['pairs']['AAVEBTC']['frames']['4h']['status']='DERIVED_BLOCKED'
        self.assertEqual(inspect(*args,NOW)['coins']['AAVE']['status'],'BLOCK')

if __name__=='__main__':unittest.main()
