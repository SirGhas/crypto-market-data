"""v5.5.1: informational close-price X/USDT divided by BTC/USDT.
No synthetic OHLCV, no liquidity proof, no publication permission, no orders.
Usage: python derived_relative_strength_v551.py [market.json] [output.json]
"""
import datetime as dt
import json
import math
import sys
import time
from pathlib import Path

COINS = ('AAVE', 'AVAX', 'LINK', 'SUI')
FRAMES = {'5m': 300, '15m': 900, '1h': 3600, '4h': 14400}
MIN_POINTS = 233
UTC = dt.timezone.utc


def verified_closes(snapshot, symbol, frame, now):
    feed = snapshot.get('pairs', {}).get(symbol, {}).get('frames', {}).get(frame, {})
    if feed.get('status') != 'available' or feed.get('source') != 'OKX Spot':
        raise ValueError('usdt_source_not_verified_okx_spot')
    raw = feed.get('candles')
    if not isinstance(raw, list):
        raise ValueError('missing_candles')
    period = FRAMES[frame]
    by_time = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError('invalid_candle')
        t, close = item.get('t'), item.get('c')
        if isinstance(t, bool) or not isinstance(t, int) or t % period:
            raise ValueError('invalid_candle_timestamp')
        try:
            close = float(close)
        except (TypeError, ValueError):
            raise ValueError('invalid_close') from None
        if not math.isfinite(close) or close <= 0:
            raise ValueError('invalid_close')
        if item.get('confirmed', True) is False or t + period > now - 2:
            continue
        if t in by_time and by_time[t] != close:
            raise ValueError('conflicting_duplicate_candle')
        by_time[t] = close
    if len(by_time) < MIN_POINTS:
        raise ValueError('insufficient_closed_candles')
    times = sorted(by_time)[-MIN_POINTS:]
    if any(b - a != period for a, b in zip(times, times[1:])):
        raise ValueError('candle_gap')
    if now - (times[-1] + period) > period + 180:
        raise ValueError('stale_closed_candle')
    return {t: by_time[t] for t in times}


def calculate(snapshot, now=None):
    if now is None:
        now = int(time.time())
    output = {
        'schema_version': '5.5.1',
        'generated_at_utc': dt.datetime.fromtimestamp(now, UTC).isoformat(),
        'kind': 'DERIVED_RELATIVE_STRENGTH',
        'research_only': True,
        'direct_btc_feed_status_override': False,
        'publication_eligible': False,
        'trade_authorization': False,
        'pairs': {},
        'limitations': [
            'Close-price ratio only; not exchange-traded X/BTC candles or OHLCV',
            'No synthetic volume, executable price, liquidity or order-book evidence',
            'Independent cross-exchange attestation not performed',
            'Direct X/BTC feeds remain UNVERIFIED where unavailable',
            'Not wired to existing score, guard, lifecycle or notification systems',
        ],
    }
    for coin in COINS:
        frames = {}
        for frame, seconds in FRAMES.items():
            try:
                asset = verified_closes(snapshot, coin + 'USDT', frame, now)
                btc = verified_closes(snapshot, 'BTCUSDT', frame, now)
                if set(asset) != set(btc):
                    raise ValueError('unaligned_candle_ids')
                times = sorted(asset)
                ratios = [asset[t] / btc[t] for t in times]
                if not all(math.isfinite(r) and r > 0 for r in ratios):
                    raise ValueError('invalid_ratio')
                frames[frame] = {
                    'status': 'DERIVED_READY',
                    'source': 'OKX Spot USDT close ratios',
                    'method': 'XUSDT_close / BTCUSDT_close',
                    'points': len(times),
                    'last_candle_id': str(times[-1]),
                    'last_closed_at_utc': dt.datetime.fromtimestamp(times[-1] + seconds, UTC).isoformat(),
                    'last_ratio': ratios[-1],
                    'ratio_change_over_window_pct': (ratios[-1] / ratios[0] - 1) * 100,
                    'series': [{'t': t, 'relative_close': r} for t, r in zip(times, ratios)],
                    'direct_btc_market_verified': False,
                    'publication_eligible': False,
                }
            except (ValueError, TypeError, KeyError, OverflowError) as exc:
                frames[frame] = {'status': 'DERIVED_BLOCKED', 'reason': str(exc), 'publication_eligible': False}
        output['pairs'][coin + 'BTC'] = {'frames': frames}
    states = [f['status'] for p in output['pairs'].values() for f in p['frames'].values()]
    output['summary'] = {'DERIVED_READY': states.count('DERIVED_READY'), 'DERIVED_BLOCKED': states.count('DERIVED_BLOCKED'), 'direct_feeds_upgraded': 0}
    return output


def main(args):
    if len(args) not in (1, 3):
        print('Usage: python derived_relative_strength_v551.py [market.json output.json]', file=sys.stderr)
        return 2
    src = Path(args[1]) if len(args) == 3 else Path('data/multisource_market.json')
    dest = Path(args[2]) if len(args) == 3 else Path('data/derived_relative_strength_v551.json')
    result = calculate(json.loads(src.read_text(encoding='utf-8')))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['summary']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
