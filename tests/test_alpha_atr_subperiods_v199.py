import unittest
from unittest.mock import patch
from engine.alpha_atr_subperiods_v199 import split,evaluate
def row(epoch,dist):return {'decision_epoch':epoch,'nearest_pair_distance_atr':str(dist)}
class AtrSubperiodTests(unittest.TestCase):
    def test_partition_and_medians(self):
        x=split([row(i,v) for i,v in enumerate(['0.1','0.2','0.3','0.4','0.5','0.6'])])
        self.assertEqual([p['mixed_windows'] for p in x],[2,2,2])
        self.assertEqual(x[0]['median_distance_atr'],'0.15')
        self.assertEqual(x[-1]['within_threshold_counts']['1'],2)
    def test_reject_duplicate_epochs(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_DECISION_EPOCH'):
            split([row(1,'1'),row(1,'2'),row(3,'3')])
    def test_reject_small_sample(self):
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT_MIXED_WINDOWS'):
            split([row(1,'1')])
    def test_safety(self):
        with patch('engine.alpha_atr_subperiods_v199.replay',return_value={'events':[]}),patch(
          'engine.alpha_atr_subperiods_v199.analyze',return_value={'details':[row(i,'1') for i in range(3)],'counts':{'mixed_windows':3}}):
            x=evaluate([(14400,10,12,9,11,100)])
        self.assertEqual(x['signals'],[])
        self.assertIsNone(x['signal_generation']['generated_signals'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
