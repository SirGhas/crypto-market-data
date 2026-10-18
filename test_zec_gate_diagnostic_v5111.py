import json
import unittest
from zec_gate_diagnostic_v5111 import compact_body, run

class DiagnosticTests(unittest.TestCase):
    def test_gate_error_body(self):
        self.assertEqual(compact_body(b'{"label":"INVALID_CURRENCY_PAIR","message":"bad pair"}')['label'], 'INVALID_CURRENCY_PAIR')

    def test_truncation(self):
        self.assertLessEqual(len(compact_body(b'x'*10000)['body_excerpt']), 500)

    def test_rejected_target_and_healthy_control(self):
        def fake(path, params=None):
            pair = path.split('/')[-1] if path.startswith('/currency_pairs/') else (params or {}).get('currency_pair')
            if path == '/currency_pairs': return {'ok': True, 'http_status': 200}, [{'id':'ZEC_USDT','base':'ZEC','quote':'USDT'}]
            if pair == 'ZEC_BTC': return {'ok': False, 'http_status': 400, 'error_response': {'label':'INVALID_CURRENCY_PAIR'}}, None
            if path.startswith('/currency_pairs/'): return {'ok': True, 'http_status': 200}, {'trade_status':'tradable','base':'BTC','quote':'USDT'}
            return {'ok': True, 'http_status': 200}, [1]
        result = run(fake)
        self.assertEqual(result['diagnosis'], 'TARGET_REJECTED_WHILE_CONTROL_WORKS')
        self.assertFalse(result['publication_approved'])
        self.assertFalse(result['gate_fallback_approved'])
        self.assertEqual(result['listed_zec_pairs'], ['ZEC_USDT'])

    def test_control_failure_is_inconclusive(self):
        def fail(path, params=None): return {'ok': False, 'http_status': 503}, None
        result = run(fail)
        self.assertEqual(result['diagnosis'], 'INCONCLUSIVE_CONTROL_FAILED')

if __name__ == '__main__': unittest.main()
