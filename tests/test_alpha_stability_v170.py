import unittest
from engine.alpha_stability_v170 import overlap_events,audit

class Test(unittest.TestCase):
    def test_overlap_inside_day(self):
        a=[{'start_epoch':86400+14400}];b=[{'start_epoch':86400}]
        self.assertEqual(len(overlap_events(a,b)),1)
        self.assertFalse(overlap_events(a,b)[0]['independent'])
    def test_nonoverlap(self):
        self.assertEqual(overlap_events([{'start_epoch':600000}],[{'start_epoch':0}]),[])
    def test_missing_history_blocks(self):
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT'):
            audit({'version':'alpha-1.6.8-btc-body-wick-probe','asset':'BTC'},[],[])
    def test_wrong_baseline_blocks(self):
        with self.assertRaisesRegex(ValueError,'BASE_REPORT'):
            audit({'version':'other','asset':'BTC'},[],[])
if __name__=='__main__':unittest.main()
