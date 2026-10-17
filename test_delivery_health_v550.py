import unittest
from delivery_health_v550 import inspect_freshness, reconcile_outbox, build


class HealthTests(unittest.TestCase):
    def test_unchanged_4h_is_expected(self):
        r = {'feeds': {'BTCUSDT:4h': {'status': 'UNCHANGED', 'age_seconds': 10000,
                                     'candle_id_changed': False, 'last_candle_id': '123'}}}
        self.assertEqual(inspect_freshness(r, 1)['UNCHANGED_EXPECTED'], ['BTCUSDT:4h'])

    def test_old_unchanged_is_stale(self):
        r = {'feeds': {'BTCUSDT:4h': {'status': 'UNCHANGED', 'age_seconds': 15000,
                                     'candle_id_changed': False, 'last_candle_id': '123'}}}
        self.assertEqual(inspect_freshness(r, 1)['STALE'], ['BTCUSDT:4h'])

    def test_unverified_not_passed(self):
        r = {'feeds': {'AAVEBTC:4h': {'status': 'UNVERIFIED', 'age_seconds': None}}}
        self.assertEqual(inspect_freshness(r, 1)['UNVERIFIED'], ['AAVEBTC:4h'])

    def test_queue_survives_empty_next_run(self):
        first, _ = reconcile_outbox({'new_publishable_events': [{'id': 'A:1'}]}, {})
        second, items = reconcile_outbox({'new_publishable_events': []}, first)
        self.assertEqual(len(items), 1)
        self.assertEqual(second['pending']['A:1']['status'], 'PENDING_DELIVERY')

    def test_no_duplicate_queue(self):
        first, _ = reconcile_outbox({'new_publishable_events': [{'id': 'A:1'}]}, {})
        _, items = reconcile_outbox({'new_publishable_events': [{'id': 'A:1'}]}, first)
        self.assertEqual(len(items), 1)

    def test_delivered_id_not_queued(self):
        _, items = reconcile_outbox({'new_publishable_events': [{'id': 'A:1'}]},
                                    {'pending': {}, 'delivered_ids': ['A:1']})
        self.assertEqual(items, [])

    def test_stale_fail_closed(self):
        with self.assertRaises(RuntimeError):
            build({'generated_at_utc': '2020-01-01T00:00:00+00:00'},
                  {'generated_at_utc': '2020-01-01T00:00:00+00:00'}, {}, 1800000000)


if __name__ == '__main__':
    unittest.main()
