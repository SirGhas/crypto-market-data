import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from engine.alpha_archive_v206 import archive
from engine.alpha_offline_replay_v207 import load_snapshot,evaluate
B=[(14400,10,12,9,11,100),(28800,11,13,10,12,150)]
class OfflineReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'snapshot.json'
        payload,self.sha=archive(B)
        self.path.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'),sort_keys=True)+'\n',encoding='utf-8')
    def tearDown(self):self.tmp.cleanup()
    def test_valid_snapshot_roundtrip(self):
        bars,quality=load_snapshot(self.path,self.sha)
        self.assertEqual(quality['bar_count'],2)
        self.assertEqual(len(bars),2)
    def test_wrong_digest_fails(self):
        with self.assertRaisesRegex(ValueError,'SNAPSHOT_SHA256_MISMATCH'):
            load_snapshot(self.path,'0'*64)
    def test_modified_file_fails(self):
        self.path.write_text(self.path.read_text().replace('150','151'),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'SNAPSHOT_SHA256_MISMATCH'):
            load_snapshot(self.path,self.sha)
    def test_safety(self):
        with patch('engine.alpha_snapshot_repro_v205.replay',return_value={'events':[]}):
            x=evaluate(self.path,self.sha)
        self.assertTrue(x['offline_replay_verified'])
        self.assertIsNone(x['signal_generation']['generated_signals'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
