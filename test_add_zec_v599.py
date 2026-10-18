import tempfile
import unittest
from pathlib import Path
from add_zec_v599 import apply, TARGETS, patch_tuple, patch_guard

class ZecIntegrationTests(unittest.TestCase):
    def test_idempotent_tuple(self):
        original="COINS=('BTC','AAVE')\n"
        once=patch_tuple(original,'COINS=')
        self.assertEqual(patch_tuple(once,'COINS='),once)
        self.assertIn("'ZEC'",once)
    def test_fail_closed_unexpected_tuple(self):
        with self.assertRaises(ValueError):
            patch_tuple("COINS=('BTC',)\n",'COINS=')
    def test_guard_requires_cross(self):
        anchor="        if e.get('tier')=='blocked': errors.append('screening_blocked')\n"
        result=patch_guard(anchor)
        self.assertIn("zec_btc_cross_not_verified_okx",result)
        self.assertEqual(result,patch_guard(result))
    def test_all_target_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for filename, marker in TARGETS.items():
                (root/filename).write_text(marker+"('BTC','AAVE')\n")
            (root/'unified_guard_v548.py').write_text("def f(e,errors):\n        if e.get('tier')=='blocked': errors.append('screening_blocked')\n")
            apply(root,True)
            first={p:p.read_text() for p in root.iterdir()}
            apply(root,True)
            self.assertEqual(first,{p:p.read_text() for p in root.iterdir()})
            self.assertTrue(all("'ZEC'" in (root/name).read_text() for name in TARGETS))
if __name__=='__main__': unittest.main()
