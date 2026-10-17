"""v5.5.2 independent, fail-closed comparison; never changes scores or publication gates."""
import datetime as dt
import json
import math
from pathlib import Path

ROOT = Path('data')
COINS = ('AAVE', 'AVAX', 'LINK', 'SUI')
FRAMES = ('5m', '15m', '1h', '4h')
MAX_AGE = 5400


def age_ok(document, now):
    try:
        stamp = dt.datetime.fromisoformat(document['generated_at_utc'].replace('Z', '+00:00'))
        return stamp.tzinfo is not None and 0 <= now - stamp.timestamp() <= MAX_AGE
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def evaluate(derived, dual, market, now):
    if not all(age_ok(doc, now) for doc in (derived, dual, market)):
        raise ValueError('stale_or_missing_input_document')
    evaluations = {e['coin']: e for e in dual.get('evaluations', []) if isinstance(e, dict) and isinstance(e.get('coin'), str)}
    results = {}
    for coin in COINS:
        item = {'status': 'AUDIT_BLOCKED', 'reason_codes': [], 'existing_score_unchanged': True,
                'publication_gate_unchanged': True, 'direct_feed_upgraded': False}
        original = evaluations.get(coin)
        frames = derived.get('pairs', {}).get(coin + 'BTC', {}).get('frames', {})
        direct = market.get('pairs', {}).get(coin + 'BTC', {}).get('frames', {})
        if not original or not isinstance(original.get('score'), (int, float)) or isinstance(original.get('score'), bool):
            item['reason_codes'].append('missing_original_screening')
        if any(direct.get(tf, {}).get('status') == 'available' for tf in FRAMES):
            item['reason_codes'].append('direct_feed_exists_review_provenance')
        for tf in FRAMES:
            f = frames.get(tf, {})
            if f.get('status') != 'DERIVED_READY' or f.get('publication_eligible') is not False or f.get('direct_btc_market_verified') is not False:
                item['reason_codes'].append(tf + ':derived_not_research_only_ready')
        four = frames.get('4h', {})
        series = four.get('series')
        if not isinstance(series, list) or len(series) != 233:
            item['reason_codes'].append('4h:invalid_series_length')
        else:
            try:
                vals = [float(v['relative_close']) for v in series]
                stamps = [int(v['t']) for v in series]
                if not all(math.isfinite(v) and v > 0 for v in vals) or any(b-a != 14400 for a,b in zip(stamps,stamps[1:])):
                    raise ValueError('invalid_values_or_gaps')
                if str(stamps[-1]) != four.get('last_candle_id') or not 0 <= now - (stamps[-1]+14400) <= 14700:
                    raise ValueError('stale_or_mismatched_last_candle')
                if not item['reason_codes']:
                    derived_bullish = vals[-1] > sum(vals) / 233
                    old = original.get('relative_strength_btc')
                    old_component = original.get('score_components', {}).get('relative_btc')
                    if old not in (None, True, False) or old_component not in (0, 5):
                        item['reason_codes'].append('original_relative_component_unexpected')
                    else:
                        item.update(status='AUDIT_READY', derived_4h_above_sma233=derived_bullish,
                                    existing_relative_btc=old, existing_relative_points=old_component,
                                    hypothetical_relative_points=5 if derived_bullish else 0,
                                    hypothetical_score_delta=(5 if derived_bullish else 0) - old_component,
                                    original_score=original['score'], original_tier=original['tier'],
                                    method='close_ratio_vs_233_point_simple_mean',
                                    source='OKX Spot USDT close ratios; not a traded BTC pair')
            except (KeyError, ValueError, TypeError, OverflowError):
                item['reason_codes'].append('4h:malformed_or_stale_series')
        results[coin] = item
    return {'schema_version': '5.5.2', 'generated_at_utc': dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),
            'mode': 'comparison_only_no_score_changes_no_publication_no_orders',
            'results': results,
            'summary': {'AUDIT_READY': sum(x['status']=='AUDIT_READY' for x in results.values()),
                        'AUDIT_BLOCKED': sum(x['status']=='AUDIT_BLOCKED' for x in results.values()),
                        'scores_modified': 0, 'publication_gates_modified': 0, 'direct_feeds_upgraded': 0},
            'limitations': ['Hypothetical deltas are NOT applied to scores or tiers',
                            'Derived price ratio is NOT proof of traded X/BTC liquidity',
                            'No direct market upgrade or signal authorization',
                            'This audit does not alter any existing scoring or guard file']}


def main():
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    derived = json.loads((ROOT/'derived_relative_strength_v551.json').read_text())
    dual = json.loads((ROOT/'dual_screen_v53.json').read_text())
    market = json.loads((ROOT/'multisource_market.json').read_text())
    report = evaluate(derived, dual, market, now)
    out = ROOT/'relative_strength_audit_v552.json'
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({'summary':report['summary'], 'coins':{k:{'status':v['status'],'hypothetical_score_delta':v.get('hypothetical_score_delta'),'reason_codes':v['reason_codes']} for k,v in report['results'].items()}}, indent=2))

if __name__ == '__main__':
    main()
