import unittest
from unittest.mock import patch
from engine.alpha_level_gaps_v204 import gaps,evaluate
def e(t,side='support',level='100'):return {'decision_epoch':t,'side':side,'level':level}
class LevelGapTests(unittest.TestCase):
    def test_gap_buckets(self):
        x=gaps([e(0),e(12*14400),e(48*14400),e(132*14400)])
        self.assertEqual(x['between_appearance_intervals'],3)
        self.assertEqual(x['gap_buckets_4h_bars'],{'up_to_12_bars':1,'13_to_36_bars':1,
          '37_to_72_bars':0,'above_72_bars':1})
    def test_duplicate_same_window_deduplicated(self):
        self.assertEqual(gaps([e(0),e(0),e(14400)])['between_appearance_intervals'],1)
    def test_misaligned_gap_fails(self):
        with self.assertRaisesRegex(ValueError,'INVALID_GAP_ALIGNMENT'):
            gaps([e(0),e(100)])
    def test_safety(self):
        with patch('engine.alpha_level_gaps_v204.replay',return_value={'events':[]}):
            x=evaluate([(14400,10,12,9,11,100)])
        self.assertEqual(x['signals'],[])
        self.assertIsNone(x['signal_generation']['generated_signals'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
