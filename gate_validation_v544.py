"""Read-only Gate.io Spot validation for BTC crosses, v5.4.4.
No orders, no collector modifications, no synthetic OHLCV.
Python 3.12 standard library only.
"""
import datetime as dt
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = 'https://api.gateio.ws/api/v4/spot'
COINS = ('AAVE', 'AVAX', 'BNB', 'LINK', 'SUI', 'XRP')
FRAMES = {'5m': 300, '15m': 900, '1h': 3600, '4h': 14400}
REQUIRED = 233
OUT = Path('data/gate_validation_v544.json')
UTC = dt.timezone.utc


def iso(ts):
    return dt.datetime.fromtimestamp(ts, UTC).isoformat()


def request_json(endpoint, params=None):
    url = BASE + endpoint
    if params:
        url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        'User-Agent': 'crypto-market-research-validation/5.4.4',
        'Accept': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP_{e.code}') from None
    except urllib.error.URLError as e:
        raise RuntimeError('network_error:' + str(e.reason)[:120]) from None


def validate_candles(raw, interval, now):
    if not isinstance(raw, list):
        raise ValueError('unexpected_candle_response')
    candles = {}
    for row in raw:
        if not isinstance(row, list) or len(row) < 7:
            raise ValueError('unexpected_candle_row')
        # Gate Spot: [timestamp, quote_volume, close, high, low, open, base_volume, ...]
        t = int(row[0]); quote_vol = float(row[1]); close = float(row[2])
        high = float(row[3]); low = float(row[4]); opn = float(row[5]); base_vol = float(row[6])
        if not all(math.isfinite(v) for v in (quote_vol, close, high, low, opn, base_vol)):
            raise ValueError('nonfinite_ohlcv')
        if min(opn, high, low, close) <= 0 or quote_vol < 0 or base_vol < 0:
            raise ValueError('invalid_price_or_volume')
        if high < max(opn, close, low) or low > min(opn, close, high):
            raise ValueError('invalid_ohlc_range')
        if t % interval:
            raise ValueError('unaligned_timestamp')
        if t + interval > now - 2:
            continue  # exclude current unfinished candle
        if t in candles:
            raise ValueError('duplicate_candle_timestamp')
        candles[t] = {'close': close, 'base_volume': base_vol, 'quote_volume': quote_vol}
    ordered = sorted(candles)
    if len(ordered) < REQUIRED:
        raise ValueError(f'insufficient_closed_candles:{len(ordered)}')
    last = ordered[-1]
    if now - (last + interval) > interval + 300:
        raise ValueError('stale_last_closed_candle')
    recent = ordered[-REQUIRED:]
    if any(b - a != interval for a, b in zip(recent, recent[1:])):
        raise ValueError('gap_in_last_233_closed_candles')
    if not any(candles[t]['base_volume'] > 0 for t in recent):
        raise ValueError('all_recent_base_volumes_zero')
    return {
        'closed_candles': len(ordered),
        'contiguous_checked': REQUIRED,
        'last_candle_id': str(last),
        'last_closed_at_utc': iso(last + interval),
        'age_seconds': now - (last + interval),
        'last_close_btc': candles[last]['close'],
        'last_base_volume': candles[last]['base_volume'],
        'nonzero_volume_candles_last_233': sum(candles[t]['base_volume'] > 0 for t in recent),
    }


def main():
    now = int(time.time())
    result = {
        'schema_version': '5.4.4',
        'generated_at_utc': iso(now),
        'exchange': 'Gate.io Spot',
        'mode': 'read_only_independent_validation',
        'required_closed_candles': REQUIRED,
        'pairs': {},
        'limitations': [
            'Gate API responses not independently attested',
            'Volume units follow Gate Spot base/quote definitions',
            'No independent price cross-check or BTC.D/USDT.D',
            'No changes to trading engine and no trade authorization',
        ],
    }
    for coin in COINS:
        pair = coin + '_BTC'
        entry = {'market': pair, 'status': 'UNVERIFIED', 'frames': {}}
        result['pairs'][coin + 'BTC'] = entry
        try:
            meta = request_json('/currency_pairs/' + urllib.parse.quote(pair, safe=''))
            if not isinstance(meta, dict) or meta.get('id') != pair:
                raise ValueError('market_identity_mismatch')
            entry['trade_status'] = meta.get('trade_status')
            if meta.get('trade_status') not in ('tradable',):
                raise ValueError('market_not_tradable')
        except Exception as exc:
            entry['reason'] = 'market_check:' + str(exc)[:150]
            continue
        for tf, interval in FRAMES.items():
            try:
                raw = request_json('/candlesticks', {
                    'currency_pair': pair, 'interval': tf, 'limit': 350,
                })
                entry['frames'][tf] = {'status': 'PASS', **validate_candles(raw, interval, now)}
            except Exception as exc:
                entry['frames'][tf] = {'status': 'UNVERIFIED', 'reason': str(exc)[:150]}
        entry['status'] = ('ELIGIBLE_FOR_CONTROLLED_INTEGRATION'
                           if all(x['status'] == 'PASS' for x in entry['frames'].values())
                           and len(entry['frames']) == len(FRAMES)
                           else 'UNVERIFIED')
    result['summary'] = {
        'pairs_checked': len(COINS),
        'eligible_pairs': [p for p, v in result['pairs'].items()
                           if v['status'] == 'ELIGIBLE_FOR_CONTROLLED_INTEGRATION'],
        'unverified_pairs': [p for p, v in result['pairs'].items()
                             if v['status'] != 'ELIGIBLE_FOR_CONTROLLED_INTEGRATION'],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['summary'], ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
