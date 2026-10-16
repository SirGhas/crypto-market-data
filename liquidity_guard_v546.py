"""v5.4.6 fail-closed XRP/BTC Gate liquidity gate for research outputs.
Does not change OHLCV, scoring weights, or OKX. Run AFTER screening engines,
BEFORE committing/publishing output. No order authorization.
"""
import datetime as dt
import json
import math
from pathlib import Path

ROOT = Path('data')
PAIR = 'XRPBTC'
TF_SECONDS = {'5m': 300, '15m': 900, '1h': 3600, '4h': 14400}
MIN_HISTORY = 233
MIN_NONZERO_FRACTION = 0.70
MIN_RELATIVE_VOLUME = 1.30


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def evaluate_gate(market, now):
    frames = market.get('pairs', {}).get(PAIR, {}).get('frames', {})
    audit = {'pair': PAIR, 'status': 'BLOCK', 'reason_codes': [], 'frames': {},
             'thresholds': {'minimum_closed_candles': MIN_HISTORY,
                            'minimum_nonzero_fraction_5m_15m': MIN_NONZERO_FRACTION,
                            'minimum_relative_volume_1h_4h': MIN_RELATIVE_VOLUME}}
    for tf, seconds in TF_SECONDS.items():
        frame = frames.get(tf, {})
        reasons = []
        if frame.get('status') != 'available' or frame.get('source') != 'Gate.io Spot':
            reasons.append('missing_or_wrong_source')
        candles = frame.get('candles', [])
        if not isinstance(candles, list) or len(candles) < MIN_HISTORY:
            reasons.append('insufficient_history')
            candles = []
        tail = candles[-MIN_HISTORY:] if candles else []
        if tail:
            try:
                ts = [int(c['t']) for c in tail]
                volumes = [float(c['v']) for c in tail]
                if any(not math.isfinite(v) or v < 0 for v in volumes):
                    reasons.append('invalid_volume')
                if any(b-a != seconds for a, b in zip(ts, ts[1:])):
                    reasons.append('noncontiguous_candles')
                age = now - (ts[-1] + seconds)
                if not 0 <= age <= seconds + 300:
                    reasons.append('stale_or_future_candle')
                fraction = sum(v > 0 for v in volumes) / len(volumes)
                baseline = sum(volumes[-21:-1]) / 20
                ratio = volumes[-1] / baseline if baseline > 0 else None
                if tf in ('5m', '15m'):
                    if fraction < MIN_NONZERO_FRACTION:
                        reasons.append('thin_market_nonzero_frequency')
                    if volumes[-1] <= 0:
                        reasons.append('last_closed_candle_zero_volume')
                else:
                    if ratio is None or ratio < MIN_RELATIVE_VOLUME:
                        reasons.append('relative_volume_not_confirmed')
                audit['frames'][tf] = {'source': frame.get('source'),
                    'last_candle_id': str(ts[-1]), 'last_closed_age_seconds': round(age, 1),
                    'nonzero_fraction': round(fraction, 4),
                    'relative_volume': round(ratio, 4) if ratio is not None else None,
                    'status': 'PASS' if not reasons else 'BLOCK', 'reasons': reasons}
            except (TypeError, ValueError, KeyError, ZeroDivisionError, OverflowError):
                reasons.append('malformed_candle_data')
        else:
            audit['frames'][tf] = {'status': 'BLOCK', 'reasons': reasons}
        audit['reason_codes'].extend(f'{tf}:{reason}' for reason in reasons)
    audit['status'] = 'PASS' if not audit['reason_codes'] else 'BLOCK'
    return audit


def apply_guard(market, dual, events, report, signals, now):
    audit = evaluate_gate(market, now)
    # Gate applies ONLY when XRP/BTC is sourced from Gate; missing cross also fails closed.
    if audit['status'] == 'PASS':
        return audit
    reason = 'xrp_btc_gate_liquidity_unconfirmed_v546'
    for item in dual.get('evaluations', []):
        if item.get('coin') == 'XRP' and item.get('tier') != 'blocked':
            item['tier'] = 'below_threshold_watch_only'
            if reason not in item.setdefault('reasons', []):
                item['reasons'].append(reason)
            item['liquidity_gate_v546'] = 'BLOCK'
            # Preserve score and score_components EXACTLY; no reweighting.
    for key in ('tier_1_top_three', 'tier_2_top_three'):
        dual[key] = [x for x in dual.get(key, []) if x.get('coin') != 'XRP']
    # Preserve order and scores; if XRP is no longer a priority, show it only as watch-only.
    dual['closest_three_below_threshold_not_buy_signals'] = sorted(
        [x for x in dual.get('evaluations', []) if x.get('tier') == 'below_threshold_watch_only'],
        key=lambda x: (x.get('score') if x.get('score') is not None else -1,
                       x.get('risk_reward_validated_levels') or -1), reverse=True)[:3]
    dual.setdefault('summary', {})['tier_1'] = sum(x.get('tier') == 'tier_1_priority_watch' for x in dual.get('evaluations', []))
    dual['summary']['tier_2'] = sum(x.get('tier') == 'tier_2_conditional_watch' for x in dual.get('evaluations', []))
    dual['liquidity_guard_v546'] = {'pair': PAIR, 'status': 'BLOCK', 'reason': reason}

    # Positive XRP events cannot be presented as actionable technical candidates.
    positive = {'4h_closed_breakout', '4h_support_reclaim', 'approaching_resistance', 'approaching_support'}
    kept = []
    for e in events.get('new_events', []):
        if e.get('coin') == 'XRP' and e.get('event_type') in positive:
            e['status'] = 'blocked_liquidity'
            e['liquidity_gate_v546'] = reason
            # Exclude from new alerts; keep audit trace below.
            audit.setdefault('suppressed_event_ids', []).append(e.get('id'))
        else:
            kept.append(e)
    events['new_events'] = kept
    events.setdefault('summary', {})['new_events'] = len(kept)
    events['summary']['forming'] = sum(e.get('status') == 'forming_watch' for e in kept)
    events['liquidity_guard_v546'] = {'pair': PAIR, 'status': 'BLOCK'}
    for e in report.get('evaluations', []):
        if e.get('coin') == 'XRP' and e.get('status') == 'candidate_requires_manual_confirmation':
            e['status'] = 'watch_only'
            if reason not in e.setdefault('reasons', []): e['reasons'].append(reason)
    report['top_three_watchlist'] = [e for e in report.get('top_three_watchlist', [])
                                     if e.get('coin') != 'XRP' or e.get('status') != 'candidate_requires_manual_confirmation']
    report['liquidity_guard_v546'] = {'pair': PAIR, 'status': 'BLOCK'}
    for e in signals.get('evaluations', []):
        if e.get('coin') == 'XRP' and e.get('status') == 'watch':
            e['status'] = 'rejected'
            if reason not in e.setdefault('reasons', []): e['reasons'].append(reason)
    signals['new_events'] = [e for e in signals.get('new_events', []) if e.get('coin') != 'XRP']
    signals.setdefault('summary', {})['new_events'] = len(signals['new_events'])
    signals['summary']['rejected'] = sum(e.get('status') == 'rejected' for e in signals.get('evaluations', []))
    signals['liquidity_guard_v546'] = {'pair': PAIR, 'status': 'BLOCK'}
    return audit


def main():
    paths = {'market': ROOT/'multisource_market.json', 'dual': ROOT/'dual_screen_v53.json',
             'events': ROOT/'events_v52.json', 'report': ROOT/'report_v51.json',
             'signals': ROOT/'signals.json'}
    docs = {name: load(path) for name, path in paths.items()}
    now = dt.datetime.now(dt.timezone.utc)
    generated = dt.datetime.fromisoformat(docs['market']['generated_at_utc'].replace('Z', '+00:00'))
    if not 0 <= (now - generated).total_seconds() <= 5400:
        raise RuntimeError('Stale market snapshot; refusing to publish guarded outputs')
    audit = apply_guard(docs['market'], docs['dual'], docs['events'], docs['report'], docs['signals'], now.timestamp())
    audit['schema_version'] = '5.4.6'
    audit['generated_at_utc'] = now.isoformat()
    audit['mode'] = 'research_only_fail_closed_no_orders'
    for name in ('dual', 'events', 'report', 'signals'):
        save(paths[name], docs[name])
    save(ROOT/'liquidity_guard_v546.json', audit)
    print(json.dumps({'pair': PAIR, 'gate': audit['status'], 'reasons': audit['reason_codes']}, ensure_ascii=False))

if __name__ == '__main__':
    main()
