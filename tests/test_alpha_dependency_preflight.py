import tempfile
import unittest
from pathlib import Path
from engine.alpha_dependency_preflight import audit

class TestAlphaDependencyPreflight(unittest.TestCase):
    def test_missing_import_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'engine').mkdir()
            (root / 'engine' / 'alpha_swing_run_v161.py').write_text('from engine.missing_module import main\n')
            report = audit(root)
            self.assertEqual(report['status'], 'BLOCKED')
            self.assertIn('engine/missing_module.py', report['missing_files'])

    def test_complete_chain_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'engine').mkdir()
            (root / 'engine' / 'alpha_swing_run_v161.py').write_text('from engine.other import main\n')
            (root / 'engine' / 'other.py').write_text('def main(): pass\n')
            self.assertEqual(audit(root)['status'], 'READY')

    def test_invalid_syntax_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'engine').mkdir()
            (root / 'engine' / 'alpha_swing_run_v161.py').write_text('from engine import (\n')
            self.assertEqual(audit(root)['status'], 'BLOCKED')

if __name__ == '__main__':
    unittest.main()
