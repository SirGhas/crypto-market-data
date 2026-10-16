"""Offline deterministic tests: python -m unittest -v test_liquidity_guard_v546.py"""
import copy
import unittest
from liquidity_guard_v546 import evaluate_gate, apply_guard

NOW = 1_800_000_000
PERIODS = {'5m': 300, '15m': 900, '1h': 3600, '4h': 14400}

def market(low_5m=False, zero_last=False):
    frames = {}
    for tf, sec in PERIODS.items():
        last = (NOW // sec - 1) * sec
        candles = []
        for i in range(233):
            vol = 1.0
            if tf == '5m' and low_5m and i < 165: vol = 0.0
            if i >= 232 and tf in ('1h', '4h'): vol = 3.0
            if i == 232 and tf == '5m' and zero_last: vol = 0.0
            candles.append({'t': last - (232-i)*sec, 'v': vol})
        frames[tf] = {'status': 'available', 'source': 'Gate.io Spot', 'candles': candles}
    return {'pairs': {'XRPBTC': {'frames': frames}}}

def outputs():
    x = {'coin': 'XRP', 'tier': 'tier_1_priority_watch', 'score': 84,
         'score_components': {'volume': 20}, 'reasons': []}
    other = {'coin': 'ETH', 'tier': 'tier_2_conditional_watch', 'score': 74, 'reasons': []}
    dual = {'evaluations': [copy.deepcopy(x), copy.deepcopy(other)],
            'tier_1_top_three': [copy.deepcopy(x)], 'tier_2_top_three': [copy.deepcopy(other)],
            'closest_three_below_threshold_not_buy_signals': [], 'summary': {'tier_1': 1, 'tier_2': 1}}
    events = {'new_events': [{'coin': 'XRP', 'id': 'x1', 'event_type': '4h_support_reclaim', 'status': 'forming_watch'},
                             {'coin': 'XRP', 'id': 'x2', 'event_type': '4h_closed_breakdown', 'status': 'technical_event_needs_context'},
                             {'coin': 'ETH', 'id': 'e1', 'event_type': '4h_support_reclaim', 'status': 'forming_watch'}],
              'summary': {'new_events': 3, 'forming': 2}}
    report = {'evaluations': [{'coin': 'XRP', 'status': 'candidate_requires_manual_confirmation', 'reasons': []}],
              'top_three_watchlist': [{'coin': 'XRP', 'status': 'candidate_requires_manual_confirmation'}]}
    signals = {'evaluations': [{'coin': 'XRP', 'status': 'watch'}],
               'new_events': [{'coin': 'XRP', 'event_id': 'x'}], 'summary': {}}
    return dual, events, report, signals

class GuardTests(unittest.TestCase):
    def test_good_market_passes_without_changes(self):
        m = market()
        self.assertEqual(evaluate_gate(m, NOW)['status'], 'PASS')
        docs = outputs()
        old = copy.deepcopy(docs)
        self.assertEqual(apply_guard(m, *docs, NOW)['status'], 'PASS')
        self.assertEqual(docs, old)

    def test_sparse_5m_blocks_without_reweighting(self):
        docs = outputs()
        audit = apply_guard(market(low_5m=True), *docs, NOW)
        self.assertEqual(audit['status'], 'BLOCK')
        self.assertEqual(docs[0]['evaluations'][0]['score'], 84)
        self.assertEqual(docs[0]['evaluations'][0]['score_components'], {'volume': 20})
        self.assertEqual(docs[0]['evaluations'][0]['tier'], 'below_threshold_watch_only')
        self.assertEqual(docs[0]['evaluations'][1]['tier'], 'tier_2_conditional_watch')
        self.assertEqual(docs[0]['tier_1_top_three'], [])
        self.assertEqual([x['id'] for x in docs[1]['new_events']], ['x2', 'e1'])
        self.assertEqual(docs[2]['evaluations'][0]['status'], 'watch_only')
        self.assertEqual(docs[3]['new_events'], [])

    def test_zero_last_5m_blocks(self):
        self.assertIn('5m:last_closed_candle_zero_volume', evaluate_gate(market(zero_last=True), NOW)['reason_codes'])

    def test_missing_cross_fails_closed(self):
        self.assertEqual(evaluate_gate({'pairs': {}}, NOW)['status'], 'BLOCK')

    def test_wrong_source_fails_closed(self):
        m = market()
        m['pairs']['XRPBTC']['frames']['4h']['source'] = 'OKX Spot'
        self.assertEqual(evaluate_gate(m, NOW)['status'], 'BLOCK')

    def test_stale_and_gaps_fail_closed(self):
        m = market()
        m['pairs']['XRPBTC']['frames']['5m']['candles'][-1]['t'] -= 300
        self.assertEqual(evaluate_gate(m, NOW)['status'], 'BLOCK')

if __name__ == '__main__': unittest.main()
