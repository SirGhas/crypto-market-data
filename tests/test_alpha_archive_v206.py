import unittest
from unittest.mock import patch
from engine.alpha_archive_v206 import archive,evaluate
B=[(14400,10,12,9,11,100),(28800,11,13,10,12,150)]
class ArchiveTests(unittest.TestCase):
    def test_snapshot_is_deterministic(self):
        a,sha=archive(B);b,sha2=archive(B)
        self.assertEqual(a,b);self.assertEqual(sha,sha2)
        self.assertEqual(a['history_quality']['bar_count'],2)
    def test_changed_price_changes_digest(self):
        _,a=archive(B)
        _,b=archive([(14400,10,12,9,11,100),(28800,11,14,10,12,150)])
        self.assertNotEqual(a,b)
    def test_invalid_history_rejected(self):
        with self.assertRaises(ValueError):
            archive([(14400,10,9,11,10,100)])
    def test_safety(self):
        with patch('engine.alpha_snapshot_repro_v205.replay',return_value={'events':[]}):
            x=evaluate(B)
        self.assertTrue(x['research_only'])
        self.assertIsNone(x['signal_generation']['generated_signals'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
