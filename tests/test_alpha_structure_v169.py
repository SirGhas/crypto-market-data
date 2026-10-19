import unittest
from engine.alpha_structure_v169 import event_groups,rank_primary

class TestStructure(unittest.TestCase):
    def test_same_event_one_level_only(self):
        z=[{'body_level':'100','events':[{'start_epoch':100,'response_atr':'1'}]},
           {'body_level':'101','events':[{'start_epoch':100,'response_atr':'2'}]}]
        g,c=event_groups(z)
        self.assertEqual(sum(len(x) for x in g.values()),1)
        self.assertEqual(len(c),1)
        self.assertEqual(len(g[1]),1)
    def test_near_time_deconflicted(self):
        z=[{'body_level':'100','events':[{'start_epoch':100,'response_atr':'1'},
           {'start_epoch':200,'response_atr':'2'}]}]
        g,_=event_groups(z)
        self.assertEqual(len(g[0]),1)
    def test_distant_events_distinct(self):
        z=[{'body_level':'100','events':[{'start_epoch':100,'response_atr':'1'},
           {'start_epoch':20000,'response_atr':'2'}]}]
        g,_=event_groups(z)
        self.assertEqual(len(g[0]),2)
    def test_bad_baseline_rejected(self):
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_BASELINE'):
            rank_primary({'version':'other','asset':'BTC'})
if __name__=='__main__':unittest.main()
