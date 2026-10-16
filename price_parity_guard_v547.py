"""Read-only market price parity audit with fail-closed research publication guard.
Only Gate.io Spot BNBBTC/XRPBTC crosses; OKX spot USDT reference, closed aligned candles.
No trade authorization, no modifications to OHLCV or scoring weights.
"""
import datetime as dt
import json
import math
from pathlib import Path

ROOT = Path('data')
PAIRS = ('BNB', 'XRP')
FRAMES = {'4h': 14400, '1h': 3600, '15m': 900, '5m': 300}
MAX_DEVIATION = 0.015  # 1.5% screening tolerance, not a claim of exchange equivalence
MIN_MATCHES = 3


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def usable(frame, expected_source, seconds, now):
    if frame.get('status') != 'available' or frame.get('source') != expected_source:
        return None, 'wrong_or_missing_source'
    candles = frame.get('candles')
    if not isinstance(candles, list) or len(candles) < 233:
        return None, 'insufficient_history'
    tail = candles[-233:]
    try:
        ts = [int(c['t']) for c in tail]
        if any(b - a != seconds for a, b in zip(ts, ts[1:])):
            return None, 'noncontiguous_candles'
        if not 0 <= now - (ts[-1] + seconds) <= seconds + 300:
            return None, 'stale_or_future_candle'
        for c in tail:
            v = float(c['c'])
            if not math.isfinite(v) or v <= 0:
                return None, 'invalid_close'
        return {int(c['t']): float(c['c']) for c in tail}, None
    except (ValueError, TypeError, KeyError, OverflowError):
        return None, 'malformed_candle'


def assess(market, coin, now):
    pairs = market.get('pairs', {})
    report = {'coin': coin, 'cross': coin + 'BTC', 'status': 'BLOCK', 'frames': {}, 'reasons': []}
    for tf, seconds in FRAMES.items():
        refs = ((coin + 'BTC', 'Gate.io Spot'), (coin + 'USDT', 'OKX Spot'), ('BTCUSDT', 'OKX Spot'))
        series = []
        errors = []
        for symbol, source in refs:
            frame = pairs.get(symbol, {}).get('frames', {}).get(tf, {})
            candles, err = usable(frame, source, seconds, now)
            series.append(candles)
            if err:
                errors.append(symbol + ':' + err)
        frame_report = {'status': 'BLOCK', 'errors': errors}
        if not errors:
            # Compare the most recent THREE identically closed candles, not nearest timestamps.
            common = sorted(set(series[0]) & set(series[1]) & set(series[2]))
            if len(common) < MIN_MATCHES or common[-1] != max(series[0]) or common[-1] != max(series[1]) or common[-1] != max(series[2]):
                errors.append('unaligned_latest_closed_candle')
            else:
                matched = common[-MIN_MATCHES:]
                deviations = []
                for stamp in matched:
                    implied = series[1][stamp] / series[2][stamp]
                    observed = series[0][stamp]
                    deviations.append(abs(observed / implied - 1))
                frame_report.update({'matched_closed_candles': MIN_MATCHES,
                                     'latest_candle_id': str(matched[-1]),
                                     'observed_gate_btc': series[0][matched[-1]],
                                     'implied_okx_btc': round(series[1][matched[-1]] / series[2][matched[-1]], 12),
                                     'max_deviation_percent': round(max(deviations) * 100, 4)})
                if max(deviations) > MAX_DEVIATION:
                    errors.append('price_deviation_above_threshold')
        if not errors:
            frame_report['status'] = 'PASS'
        else:
            report['reasons'].extend(tf + ':' + e for e in errors)
        frame_report['errors'] = errors
        report['frames'][tf] = frame_report
    report['status'] = 'PASS' if not report['reasons'] else 'BLOCK'
    return report


def suppress(coin, dual, events, report, signals, audit):
    reason = 'gate_btc_price_parity_unconfirmed_v547'
    for item in dual.get('evaluations', []):
        if item.get('coin') == coin and item.get('tier') not in ('blocked', 'below_threshold_watch_only'):
            item['tier'] = 'below_threshold_watch_only'
            if reason not in item.setdefault('reasons', []):
                item['reasons'].append(reason)
            item['price_parity_guard_v547'] = 'BLOCK'
    for key in ('tier_1_top_three', 'tier_2_top_three'):
        dual[key] = [x for x in dual.get(key, []) if x.get('coin') != coin]
    dual['closest_three_below_threshold_not_buy_signals'] = sorted(
        [x for x in dual.get('evaluations', []) if x.get('tier') == 'below_threshold_watch_only'],
        key=lambda x: (x.get('score') if x.get('score') is not None else -1,
                       x.get('risk_reward_validated_levels') or -1), reverse=True)[:3]
    dual.setdefault('summary', {})['tier_1'] = sum(x.get('tier') == 'tier_1_priority_watch' for x in dual.get('evaluations', []))
    dual['summary']['tier_2'] = sum(x.get('tier') == 'tier_2_conditional_watch' for x in dual.get('evaluations', []))
    positive = {'4h_closed_breakout', '4h_support_reclaim', 'approaching_resistance', 'approaching_support'}
    kept = []
    for event in events.get('new_events', []):
        if event.get('coin') == coin and event.get('event_type') in positive:
            audit.setdefault('suppressed_event_ids', []).append(event.get('id'))
        else:
            kept.append(event)
    events['new_events'] = kept
    events.setdefault('summary', {})['new_events'] = len(kept)
    events['summary']['forming'] = sum(x.get('status') == 'forming_watch' for x in kept)
    for item in report.get('evaluations', []):
        if item.get('coin') == coin and item.get('status') == 'candidate_requires_manual_confirmation':
            item['status'] = 'watch_only'
            if reason not in item.setdefault('reasons', []): item['reasons'].append(reason)
    report['top_three_watchlist'] = [x for x in report.get('top_three_watchlist', []) if x.get('coin') != coin]
    for item in signals.get('evaluations', []):
        if item.get('coin') == coin and item.get('status') == 'watch':
            item['status'] = 'rejected'
            if reason not in item.setdefault('reasons', []): item['reasons'].append(reason)
    signals['new_events'] = [x for x in signals.get('new_events', []) if x.get('coin') != coin]
    signals.setdefault('summary', {})['new_events'] = len(signals['new_events'])
    signals['summary']['rejected'] = sum(x.get('status') == 'rejected' for x in signals.get('evaluations', []))


def main():
    paths = {'market': ROOT/'multisource_market.json', 'dual': ROOT/'dual_screen_v53.json',
             'events': ROOT/'events_v52.json', 'report': ROOT/'report_v51.json',
             'signals': ROOT/'signals.json'}
    docs = {name: load(path) for name, path in paths.items()}
    now = dt.datetime.now(dt.timezone.utc)
    stamp = dt.datetime.fromisoformat(docs['market']['generated_at_utc'].replace('Z', '+00:00'))
    if not 0 <= (now - stamp).total_seconds() <= 5400:
        raise RuntimeError('Stale source snapshot; refusing parity publication')
    audits = {coin: assess(docs['market'], coin, now.timestamp()) for coin in PAIRS}
    for coin, audit in audits.items():
        if audit['status'] != 'PASS':
            suppress(coin, docs['dual'], docs['events'], docs['report'], docs['signals'], audit)
    for name in ('dual', 'events', 'report', 'signals'):
        save(paths[name], docs[name])
    result = {'schema_version': '5.4.7', 'generated_at_utc': now.isoformat(),
              'mode': 'fail_closed_research_only_no_trades', 'max_deviation_percent': MAX_DEVIATION * 100,
              'pairs': audits, 'limitations': ['Comparison uses aligned closed candles and OKX implied cross, not independent price attestation',
                                              'No order-book liquidity, execution prices or BTC.D/USDT.D verification',
                                              'No changes to original scores, scoring weights or collector']}
    save(ROOT/'price_parity_guard_v547.json', result)
    print(json.dumps({k: v['status'] for k, v in audits.items()}))


if __name__ == '__main__':
    main()
