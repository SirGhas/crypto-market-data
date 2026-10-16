"""Auditable candle freshness snapshots, stdlib only (v5.4.1).
Usage: python freshness_report_v54.py data/multisource_market.json data/freshness_report_v54.json
Informational report; the existing integrity gate remains authoritative.
"""
import datetime as dt
import json
import math
import sys
from pathlib import Path

UTC = dt.timezone.utc
INTERVALS = {'5m': 300, '15m': 900, '1h': 3600, '4h': 14400}

def iso(timestamp):
    return dt.datetime.fromtimestamp(timestamp, UTC).isoformat()

def timestamp(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError('invalid_timestamp')
    return int(value)

def prior_feed(previous, key):
    return previous.get('feeds', {}).get(key, {}) if isinstance(previous, dict) else {}

def inspect_feed(frame, tf, now, old):
    result = {'status': 'UNVERIFIED', 'source': frame.get('source') if isinstance(frame, dict) else None,
              'last_candle_id': None, 'last_candle_open_utc': None, 'last_closed_at_utc': None,
              'age_seconds': None, 'last_close': None, 'last_volume': None,
              'previous_candle_id': old.get('last_candle_id'), 'previous_close': old.get('last_close'),
              'candle_id_changed': None, 'close_change': None, 'reasons': []}
    if not isinstance(frame, dict) or frame.get('status') != 'available':
        result['reasons'].append('feed_unavailable')
        return result
    candles = frame.get('candles')
    if not isinstance(candles, list) or not candles:
        result['reasons'].append('missing_candles')
        return result
    try:
        last = candles[-1]
        t = timestamp(last['t'])
        interval = INTERVALS[tf]
        close = float(last['c'])
        volume = float(last['v'])
        if not (math.isfinite(close) and close > 0 and math.isfinite(volume) and volume >= 0):
            raise ValueError('invalid_close_or_volume')
        if t % interval or last.get('confirmed', True) is False or t + interval > now:
            raise ValueError('unclosed_or_unaligned_candle')
        age = now - (t + interval)
        result.update(last_candle_id=str(t), last_candle_open_utc=iso(t),
                      last_closed_at_utc=iso(t + interval), age_seconds=round(age),
                      last_close=close, last_volume=volume)
        old_id = old.get('last_candle_id')
        if old_id is not None:
            result['candle_id_changed'] = str(old_id) != str(t)
            if old.get('last_close') is not None:
                result['close_change'] = round(close - float(old['last_close']), 12)
        if age > interval + 300:
            result['status'] = 'STALE'
            result['reasons'].append('last_closed_candle_too_old')
        elif old_id is not None and str(old_id) == str(t):
            result['status'] = 'UNCHANGED'
            result['reasons'].append('same_closed_candle_as_previous_run_not_necessarily_stale')
        else:
            result['status'] = 'PASS'
        if old_id is not None and int(old_id) > t:
            result['status'] = 'UNVERIFIED'
            result['reasons'].append('candle_timestamp_regressed')
        if old_id is not None and str(old_id) == str(t) and old.get('last_close') is not None and float(old['last_close']) != close:
            result['status'] = 'UNVERIFIED'
            result['reasons'].append('same_candle_id_different_close')
        if old.get('source') and old['source'] != result['source']:
            result['reasons'].append('exchange_source_changed')
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        result['status'] = 'UNVERIFIED'
        result['reasons'].append('invalid_feed_data:' + str(exc))
    return result

def build(snapshot, previous, now):
    feeds = {}
    pairs = snapshot.get('pairs', {})
    for symbol, pair in sorted(pairs.items()):
        for tf in INTERVALS:
            key = f'{symbol}:{tf}'
            feeds[key] = inspect_feed(pair.get('frames', {}).get(tf, {}), tf, now, prior_feed(previous, key))
    counts = {s: sum(f['status'] == s for f in feeds.values()) for s in ('PASS', 'STALE', 'UNCHANGED', 'UNVERIFIED')}
    return {'schema_version': '5.4.1', 'generated_at_utc': iso(now),
            'source_snapshot_generated_at_utc': snapshot.get('generated_at_utc'),
            'previous_report_generated_at_utc': previous.get('generated_at_utc'),
            'status': 'REVIEW_REQUIRED' if counts['STALE'] or counts['UNVERIFIED'] else 'OK',
            'summary': counts, 'feeds': feeds,
            'limitations': ['Exchange identity is as reported by the collector, not independently attested',
                            'No independent Binance/TradingView price comparison',
                            'UNCHANGED is normal until a new candle is due',
                            'No BTC.D or USDT.D verification', 'No trading authorization']}

def main(argv):
    if len(argv) != 3:
        print('Usage: python freshness_report_v54.py <snapshot.json> <report.json>', file=sys.stderr)
        return 2
    source, target = map(Path, argv[1:])
    try:
        snapshot = json.loads(source.read_text(encoding='utf-8'))
        previous = json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
        report = build(snapshot, previous, int(dt.datetime.now(UTC).timestamp()))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'status': report['status'], 'summary': report['summary']}))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print('Freshness report generation failed: ' + str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main(sys.argv))
