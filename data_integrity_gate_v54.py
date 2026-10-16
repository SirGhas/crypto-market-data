"""Fail-closed OHLCV integrity gate for crypto-market-data (Python 3.12 stdlib).
Run before screening; validates a snapshot, not exchange provenance.
Usage: python data_integrity_gate_v54.py data/multisource_market.json
Exit 0 = structural and timing checks passed; exit 2 = blocked.
"""
import datetime as dt
import json
import math
import sys
from pathlib import Path

FRAMES = {'4h': 14400, '1h': 3600, '15m': 900}
COINS = ('BTC', 'ETH', 'BNB', 'SOL', 'LTC', 'LINK', 'XRP', 'AVAX', 'SUI', 'AAVE')
UTC = dt.timezone.utc

def iso(ts):
    return dt.datetime.fromtimestamp(ts, UTC).isoformat()

def check_frame(frame, interval, now):
    issues = []
    if frame.get('status') != 'available':
        return ['frame_unavailable']
    cs = frame.get('candles')
    if not isinstance(cs, list) or len(cs) < 234:
        return ['insufficient_candles']
    previous = None
    for i, c in enumerate(cs):
        try:
            t = c['t']
            if not isinstance(t, (int, float)) or isinstance(t, bool) or not math.isfinite(t):
                raise ValueError('invalid_timestamp')
            o, h, l, close, vol = (float(c[k]) for k in ('o','h','l','c','v'))
            if not all(map(math.isfinite, (o,h,l,close,vol))) or min(o,h,l,close) <= 0 or vol < 0:
                raise ValueError('invalid_price_or_volume')
            if h < max(o,close,l) or l > min(o,close,h):
                raise ValueError('invalid_ohlc_range')
            if t % interval != 0:
                raise ValueError('unaligned_timestamp')
            if previous is not None and t - previous != interval:
                raise ValueError('gap_or_duplicate_timestamp')
            if t + interval > now:
                raise ValueError('forming_or_future_candle')
            previous = t
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            issues.append(f'candle_{i}:{exc}')
            if len(issues) >= 5:
                break
    if not issues and not 0 <= now - (cs[-1]['t'] + interval) <= interval + 300:
        issues.append('stale_last_closed_candle')
    return issues

def inspect(data, now):
    result = {'checked_at_utc':iso(now),'status':'PASS','checks':{},'limitations':[
        'Exchange provenance NOT verified', 'Binance independent comparison NOT performed',
        'BTC.D and USDT.D NOT verified', 'No trade authorization']}
    pairs = data.get('pairs', {})
    for coin in COINS:
        pair = coin+'USDT'
        frames = pairs.get(pair, {}).get('frames', {})
        for tf, sec in FRAMES.items():
            issues = check_frame(frames.get(tf, {}), sec, now)
            result['checks'][f'{pair}:{tf}'] = {'status':'PASS' if not issues else 'BLOCK','reasons':issues}
            if issues:
                result['status'] = 'BLOCK'
    return result

def main():
    if len(sys.argv) != 2:
        print('Usage: python data_integrity_gate_v54.py <snapshot.json>',file=sys.stderr)
        return 2
    now = dt.datetime.now(UTC).timestamp()
    try:
        data = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
        result = inspect(data, now)
    except (OSError, ValueError, TypeError) as exc:
        result = {'status':'BLOCK','reasons':[f'input_error:{exc}']}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status']=='PASS' else 2

if __name__ == '__main__':
    sys.exit(main())
