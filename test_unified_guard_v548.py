import unittest
from unified_guard_v548 import band,evaluate,publication_events

class GuardTests(unittest.TestCase):
    def test_bands(self):
        self.assertEqual([band(x) for x in (None,59,60,69,70,79,80,100)],
          ['blocked_gray','gray_below_60','yellow_60_69','yellow_60_69',
           'blue_70_79','blue_70_79','green_80_100','green_80_100'])
    def test_fail_closed_missing_market(self):
        dual={'evaluations':[{'coin':'SUI','score':65,'tier':'tier_2_conditional_watch'}]}
        out=evaluate({},dual,{}, {},100000)
        self.assertEqual(out['coins']['SUI']['positive_publication_gate'],'BLOCK')
        self.assertEqual(out['bands']['yellow_60_69'],['SUI'])
        self.assertEqual(dual['evaluations'][0]['score'],65)
    def test_parity_block(self):
        dual={'evaluations':[{'coin':'BNB','score':81,'tier':'tier_1_priority_watch'}]}
        out=evaluate({},dual,{}, {'pairs':{'BNB':{'status':'BLOCK'}}},100000)
        self.assertIn('price_parity_unconfirmed',out['coins']['BNB']['reason_codes'])
    def test_xrp_liquidity_block(self):
        dual={'evaluations':[{'coin':'XRP','score':75,'tier':'tier_2_conditional_watch'}]}
        out=evaluate({},dual,{'status':'BLOCK'},{'pairs':{'XRP':{'status':'PASS'}}},100000)
        self.assertIn('xrp_btc_liquidity_unconfirmed',out['coins']['XRP']['reason_codes'])
    def test_negative_events_remain(self):
        audit={'coins':{'XRP':{'positive_publication_gate':'BLOCK'}}}
        events={'new_events':[{'coin':'XRP','event_type':'4h_closed_breakout'},
                              {'coin':'XRP','event_type':'4h_closed_breakdown'}]}
        self.assertEqual(len(publication_events(events,audit)),1)
        self.assertEqual(publication_events(events,audit)[0]['event_type'],'4h_closed_breakdown')
    def test_no_mutation(self):
        dual={'evaluations':[{'coin':'SUI','score':60,'tier':'tier_2_conditional_watch','score_components':{'volume':15}}]}
        evaluate({},dual,{}, {},100000)
        self.assertEqual(dual['evaluations'][0]['score_components']['volume'],15)

if __name__=='__main__':unittest.main()
