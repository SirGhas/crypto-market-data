import tempfile,unittest
from pathlib import Path
from event_aligned_v598 import audit_pair,replay_file,restart_simulation,evaluate

class Tests(unittest.TestCase):
    def test_missing_feeds_fail_closed(self):
        self.assertEqual(audit_pair({'pairs':{}},'ETH')['status'],'UNVERIFIED')
    def test_restart(self):
        self.assertEqual(restart_simulation()['status'],'PASS_DRY_RESTART')
    def test_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.json';e={'id':'a','eligible':True,'confirmed':True}
            self.assertEqual(replay_file(p,[e])['accepted'],1)
            self.assertEqual(replay_file(p,[e])['duplicates'],1)
    def test_unconfirmed_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            r=replay_file(Path(d)/'s.json',[{'id':'b','eligible':True,'confirmed':False}])
            self.assertEqual((r['blocked'],r['pending']),(1,0))
    def test_injected_failure_preserves_state(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.json';replay_file(p,[]);original=p.read_bytes()
            with self.assertRaises(OSError):replay_file(p,[{'id':'a','eligible':True,'confirmed':True}],True)
            self.assertEqual(p.read_bytes(),original)
    def test_outbox_collision_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.json';p.write_text('{"pending":{"a":{}},"delivered_ids":["a"]}')
            with self.assertRaises(ValueError):replay_file(p,[])
    def test_stale_market_blocks(self):
        self.assertEqual(evaluate({'generated_at_utc':'2020-01-01T00:00:00+00:00'},2000000000)['status'],'BLOCK')
if __name__=='__main__':unittest.main()
