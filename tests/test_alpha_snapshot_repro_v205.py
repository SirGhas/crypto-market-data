import unittest
from unittest.mock import patch
from engine.alpha_snapshot_repro_v205 import reconcile,evaluate
BARS=[(14400,10,12,9,11,100)]
def e(t):return {'decision_epoch':t,'side':'support','level':'100'}
class SnapshotReproTests(unittest.TestCase):
    def test_same_input_replay_reconciles(self):
        with patch('engine.alpha_snapshot_repro_v205.replay',return_value={
          'events':[e(14400),e(28800)]}):
            x=reconcile(BARS)
        self.assertTrue(x['replay_deterministic'])
        self.assertEqual(x['gap_counts']['repeated_exact_identities'],1)
        self.assertEqual(x['recurrence_counts']['identities_in_multiple_windows'],1)
    def test_changed_replay_fails_closed(self):
        with patch('engine.alpha_snapshot_repro_v205.replay',side_effect=[
          {'events':[e(14400)]},{'events':[e(28800)]}]):
            with self.assertRaisesRegex(ValueError,'NONDETERMINISTIC_EVENT_REPLAY'):
                reconcile(BARS)
    def test_history_fingerprint_present(self):
        with patch('engine.alpha_snapshot_repro_v205.replay',return_value={'events':[]}):
            x=reconcile(BARS)
        self.assertEqual(len(x['history_quality']['sha256_normalized_history']),64)
    def test_safety(self):
        with patch('engine.alpha_snapshot_repro_v205.replay',return_value={'events':[]}):
            x=evaluate(BARS)
        self.assertEqual(x['signals'],[])
        self.assertIsNone(x['signal_generation']['generated_signals'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
