import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from engine.alpha_cross_run_replay_v208 import verify

class CrossRunReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.snapshot = Path(self.tmp.name) / 'snapshot.json'
        self.snapshot.write_text('{}')
        self.report = Path(self.tmp.name) / 'report.json'
        self.source = {'snapshot_file_sha256': 'a'*64, 'replay_event_count': 3,
                       'recurrence_counts': {'repeated': 1},
                       'history_quality': {'bar_count': 2}, 'gap_counts': {}}
        self.report.write_text(json.dumps(self.source))
        self.source_replay = Path(self.tmp.name) / 'source_replay.json'
        self.source_replay.write_text(json.dumps({'snapshot_file_sha256': 'a'*64, 'gap_counts': {}}))
        self.replay = {'event_count': 3, 'recurrence_counts': {'repeated': 1},
                       'history_quality': {'bar_count': 2}, 'gap_counts': {}}
    def tearDown(self):
        self.tmp.cleanup()
    @patch('engine.alpha_cross_run_replay_v208.offline_evaluate')
    def test_independent_replay(self, mock):
        mock.return_value = self.replay
        result = verify(self.snapshot, self.report, 'a'*64, '100', '200', self.source_replay)
        self.assertTrue(result['cross_run_verified'])
        self.assertFalse(result['trading_enabled'])
        self.assertIsNone(result['signal_generation']['generated_signals'])
        mock.assert_called_once()
    def test_same_run_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_RUN_MUST_BE_INDEPENDENT'):
            verify(self.snapshot, self.report, 'a'*64, '100', '100', self.source_replay)
    def test_wrong_digest_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_SNAPSHOT_DIGEST_MISMATCH'):
            verify(self.snapshot, self.report, 'b'*64, '100', '200', self.source_replay)
    @patch('engine.alpha_cross_run_replay_v208.offline_evaluate')
    def test_count_mismatch_rejected(self, mock):
        mock.return_value = dict(self.replay, event_count=4)
        with self.assertRaisesRegex(ValueError, 'CROSS_RUN_EVENT_COUNT_MISMATCH'):
            verify(self.snapshot, self.report, 'a'*64, '100', '200', self.source_replay)
    @patch('engine.alpha_cross_run_replay_v208.offline_evaluate')
    def test_recurrence_mismatch_rejected(self, mock):
        mock.return_value = dict(self.replay, recurrence_counts={})
        with self.assertRaisesRegex(ValueError, 'CROSS_RUN_RECURRENCE_MISMATCH'):
            verify(self.snapshot, self.report, 'a'*64, '100', '200', self.source_replay)
    @patch('engine.alpha_cross_run_replay_v208.offline_evaluate')
    def test_gap_mismatch_rejected(self, mock):
        mock.return_value = dict(self.replay, gap_counts={'different': 1})
        with self.assertRaisesRegex(ValueError, 'CROSS_RUN_GAP_COUNTS_MISMATCH'):
            verify(self.snapshot, self.report, 'a'*64, '100', '200', self.source_replay)
    def test_missing_snapshot_fails(self):
        with self.assertRaises(FileNotFoundError):
            verify(self.snapshot.with_name('missing.json'), self.report, 'a'*64, '100', '200', self.source_replay)
    def test_missing_report_fails(self):
        with self.assertRaises(FileNotFoundError):
            verify(self.snapshot, self.report.with_name('missing.json'), 'a'*64, '100', '200', self.source_replay)

if __name__ == '__main__':
    unittest.main()
