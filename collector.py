"""Hourly Kraken OHLC collector. Python 3.12, no external dependencies."""
import datetime as dt
import json
import time
import urllib.request
from pathlib import Path

COINS = ['BTC', 'ETH', 'BNB', 'SOL', 'LTC', 'LINK', 'XRP', 'AVAX', 'SUI', 'AAVE']
FRAMES = {'5m': 5, '15m': 15, '1h': 60, '4h': 240}
DERIVED_BTC = {'BNB', 'AVAX', 'SUI'}
BASE = 'https://api.kraken.com/0/public/OHLC'
OUTPUT = Path('data/market.json')


def request(pair, interval):
    req = urllib.request.Request(
        f'{BASE}?pair={pair}&interval={interval}',
        headers={'User-Agent': 'PortfolioResearch/2.0'},
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        data = json.load(response)
    if data.get('error'):
        raise ValueError(str(data['error']))
    key = next(k for k in data['result'] if k != 'last')
    # Kraken's final OHLC entry is an unclosed candle: NEVER use it.
    return [
        {'t': int(r[0]), 'o': float(r[1]), 'h': float(r[2]),
         'l': float(r[3]), 'c': float(r[4]), 'v': float(r[6])}
        for r in data['result'][key][:-1][-300:]
    ]


def indicators(rows, timeframe_minutes, now_ts, has_real_volume=True):
    if not rows:
        return {'valid': False, 'reason': 'no_closed_candles'}
    age = now_ts - (rows[-1]['t'] + timeframe_minutes * 60)
    # A stale feed must not be eligible for trading signals.
    # Kraken may have occasional gaps; allow up to two full frame durations.
    freshness = age <= max(0, 2 * timeframe_minutes * 60)
    if len(rows) < 234:
        return {'valid': False, 'reason': 'insufficient_closed_candles',
                'closed_candle_count': len(rows), 'fresh': freshness}
    if not freshness:
        return {'valid': False, 'reason': 'stale_closed_candle',
                'age_seconds': round(age), 'fresh': False}
    close = [x['c'] for x in rows]
    vol = [x['v'] for x in rows] if has_real_volume else []
    avg = sum(vol[-21:-1]) / 20 if has_real_volume else None
    return {
        'valid': True, 'fresh': True, 'close': close[-1],
        'last_candle_start_utc': rows[-1]['t'],
        'age_seconds': round(age),
        'sma233': sum(close[-233:]) / 233,
        'relative_volume20': (vol[-1] / avg if avg else None),
        'volume_confirmation_available': has_real_volume,
        'prior20_high': max(x['h'] for x in rows[-21:-1]),
        'prior20_low': min(x['l'] for x in rows[-21:-1]),
    }


def derive_cross(asset_rows, btc_rows):
    """Synchronize candle timestamps; use USD OHLC to approximate X/BTC.

    Open/close ratios are exact ratios of the sampled USD prices. High/low
    ratios are conservative envelopes, NOT exact traded cross-pair extremes.
    Synthetic volume is intentionally omitted.
    """
    btc_by_time = {r['t']: r for r in btc_rows}
    output = []
    for a in asset_rows:
        b = btc_by_time.get(a['t'])
        if not b or min(b['o'], b['h'], b['l'], b['c']) <= 0:
            continue
        output.append({
            't': a['t'], 'o': a['o'] / b['o'],
            'h': a['h'] / b['l'], 'l': a['l'] / b['h'],
            'c': a['c'] / b['c'], 'v': None,
        })
    return output[-300:]


def main():
    now = dt.datetime.now(dt.timezone.utc)
    now_ts = now.timestamp()
    out = {
        'schema_version': 2, 'generated_at_utc': now.isoformat(),
        'source': 'Kraken public OHLC', 'quote': 'USD, not USDT',
        'forming_candle_excluded': True,
        'dominance': {
            'BTC.D': {'status': 'unavailable', 'reason': 'No verified dominance OHLCV source configured'},
            'USDT.D': {'status': 'unavailable', 'reason': 'No verified dominance OHLCV source configured'},
        },
        'markets': {}, 'summary': {},
    }
    direct_success = derived_success = 0
    errors = []
    for coin in COINS:
        out['markets'][coin] = {}
        # Don't call unavailable direct BTC pairs; derive them below.
        quotes = ['USD'] if coin == 'BTC' or coin in DERIVED_BTC else ['USD', 'XBT']
        for quote in quotes:
            pair = ('XBT' if coin == 'BTC' else coin) + quote
            name = coin + '/' + ('BTC' if quote == 'XBT' else 'USD')
            for tf, minutes in FRAMES.items():
                try:
                    rows = request(pair, minutes)
                    out['markets'][coin].setdefault(name, {})[tf] = {
                        'pair': pair, 'origin': 'kraken_direct', 'candles': rows,
                        'indicators': indicators(rows, minutes, now_ts),
                    }
                    direct_success += 1
                except Exception as exc:
                    msg = str(exc)
                    out['markets'][coin].setdefault(name, {})[tf] = {'pair': pair, 'error': msg}
                    errors.append({'coin': coin, 'pair': name, 'timeframe': tf, 'error': msg})
                time.sleep(0.35)

    for coin in sorted(DERIVED_BTC):
        for tf, minutes in FRAMES.items():
            name = coin + '/BTC'
            try:
                asset = out['markets'][coin][coin + '/USD'][tf]['candles']
                btc = out['markets']['BTC']['BTC/USD'][tf]['candles']
                rows = derive_cross(asset, btc)
                if not rows:
                    raise ValueError('No timestamp-aligned USD candles')
                out['markets'][coin].setdefault(name, {})[tf] = {
                    'pair': name, 'origin': 'derived_from_usd_close_ratio',
                    'volume_source': 'unavailable',
                    'high_low_method': 'conservative_OHLC_envelope_not_exact_cross_extrema',
                    'candles': rows,
                    'indicators': indicators(rows, minutes, now_ts, has_real_volume=False),
                }
                derived_success += 1
            except Exception as exc:
                msg = str(exc)
                out['markets'][coin].setdefault(name, {})[tf] = {'pair': name, 'error': msg}
                errors.append({'coin': coin, 'pair': name, 'timeframe': tf, 'error': msg})

    total = direct_success + derived_success
    out['summary'] = {
        'successful_feeds': total, 'attempted_feeds': 76,
        'direct_feeds': direct_success, 'derived_feeds': derived_success,
        'error_count': len(errors), 'errors': errors,
        'signal_eligible_feeds': sum(
            1 for pairs in out['markets'].values() for frames in pairs.values()
            for item in frames.values() if item.get('indicators', {}).get('valid')
        ),
    }
    if total == 0:
        raise RuntimeError('No successful market feeds; refusing to overwrite previous snapshot')
    OUTPUT.parent.mkdir(exist_ok=True)
    temp = OUTPUT.with_suffix('.json.tmp')
    temp.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    temp.replace(OUTPUT)
    print(json.dumps(out['summary']))


if __name__ == '__main__':
    main()
