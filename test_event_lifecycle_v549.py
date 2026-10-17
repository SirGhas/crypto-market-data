import unittest
from event_lifecycle_v549 import reconcile, run


def event(id='XRP:4h_closed_breakout:100', coin='XRP', typ='4h_closed_breakout'):
    return {'id': id, 'coin': coin, 'event_type': typ, 'status': 'forming_watch'}


class LifecycleTests(unittest.TestCase):
    def test_blocked_not_marked_emitted(self):
        state, new, pending = reconcile([event()], {'coins': {'XRP': {'positive_publication_gate': 'BLOCK'}}}, {})
        self.assertEqual(new, [])
        self.assertEqual(len(pending), 1)
        self.assertEqual(state['emitted_ids'], [])

    def test_later_pass_emits_once(self):
        blocked = {'coins': {'XRP': {'positive_publication_gate': 'BLOCK'}}}
        passed = {'coins': {'XRP': {'positive_publication_gate': 'PASS'}}}
        state, _, _ = reconcile([event()], blocked, {})
        state, new, _ = reconcile([event()], passed, state)
        self.assertEqual(len(new), 1)
        state, new, _ = reconcile([event()], passed, state)
        self.assertEqual(new, [])

    def test_negative_event_independent_of_positive_gate(self):
        e = event('XRP:4h_closed_breakdown:100', typ='4h_closed_breakdown')
        state, new, pending = reconcile([e], {'coins': {'XRP': {'positive_publication_gate': 'BLOCK'}}}, {})
        self.assertEqual(new, [e])
        self.assertFalse(pending)

    def test_new_candle_new_id(self):
        passed = {'coins': {'XRP': {'positive_publication_gate': 'PASS'}}}
        state, _, _ = reconcile([event()], passed, {})
        _, new, _ = reconcile([event('XRP:4h_closed_breakout:200')], passed, state)
        self.assertEqual(len(new), 1)

    def test_invalid_ids_ignored(self):
        state, new, pending = reconcile([{'coin': 'XRP', 'event_type': '4h_closed_breakout'}], {}, {})
        self.assertEqual((new, pending, state['emitted_ids']), ([], [], []))

    def test_stale_inputs_fail_closed(self):
        with self.assertRaises(RuntimeError):
            run({'generated_at_utc': '2020-01-01T00:00:00+00:00'}, {}, {}, 1800000000)


if __name__ == '__main__':
    unittest.main()
