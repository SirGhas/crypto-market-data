"""Read-only source feasibility probe v5.4.3. No trades, no engine modifications."""
import datetime as dt
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

COINS = ('AAVE', 'AVAX', 'BNB', 'LINK', 'SUI', 'XRP')
SECONDS = 14400
NEEDED = 233
NOW = int(time.time())
OUT = Path('data/source_probe_v543.json')


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'crypto-market-research-source-probe/5.4.3', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'HTTP_{exc.code}') from None
    except urllib.error.URLError as exc:
        raise RuntimeError('network_error:' + str(exc.reason)[:100]) from None


def kraken_markets():
    data = get('https://api.kraken.com/0/public/AssetPairs')
    if data.get('error'):
        raise ValueError('kraken_api_error:' + str(data['error'])[:100])
    pairs = data['result']
    # Exact base/quote mapping via exchange-provided wsname; never guess a ticker alias.
    return {v.get('wsname', '').upper(): k for k, v in pairs.items() if v.get('wsname')}


def kraken_candles(pair):
    q = urllib.parse.urlencode({'pair': pair, 'interval': 240})
    data = get('https://api.kraken.com/0/public/OHLC?' + q)
    if data.get('error'):
        raise ValueError('kraken_api_error:' + str(data['error'])[:100])
    keys = [k for k in data['result'] if k != 'last']
    if len(keys) != 1:
        raise ValueError('unexpected_kraken_result')
    # Kraken returns the current, uncommitted candle: filter by closing time.
    return [{'t': int(r[0]), 'o': float(r[1]), 'h': float(r[2]), 'l': float(r[3]), 'c': float(r[4]), 'v': float(r[6])} for r in data['result'][keys[0]]]


def gate_markets():
    data = get('https://api.gateio.ws/api/v4/spot/currency_pairs')
    if not isinstance(data, list):
        raise ValueError('unexpected_gate_markets')
    return {x['id']: x for x in data if isinstance(x, dict) and 'id' in x}


def gate_candles(pair):
    q = urllib.parse.urlencode({'currency_pair': pair, 'interval': '4h', 'limit': 300})
    data = get('https://api.gateio.ws/api/v4/spot/candlesticks?' + q)
    if not isinstance(data, list):
        raise ValueError('unexpected_gate_candles')
    # Gate response: [timestamp, quote_volume, close, high, low, open, base_volume, ...]
    return [{'t': int(r[0]), 'o': float(r[5]), 'h': float(r[3]), 'l': float(r[4]), 'c': float(r[2]), 'v': float(r[6])} for r in data]


def assess(rows, now):
    clean = {}
    for r in rows:
        t = r['t']
        if t % SECONDS or t + SECONDS > now:
            continue
        vals = [r[k] for k in ('o', 'h', 'l', 'c', 'v')]
        if not all(math.isfinite(x) for x in vals) or min(vals[:4]) <= 0 or vals[4] < 0:
            return {'status': 'INVALID_OHLCV', 'closed_candles': len(clean)}
        if r['h'] < max(r['o'], r['c'], r['l']) or r['l'] > min(r['o'], r['c'], r['h']):
            return {'status': 'INVALID_OHLCV', 'closed_candles': len(clean)}
        if t in clean and clean[t] != r:
            return {'status': 'CONFLICTING_DUPLICATES', 'closed_candles': len(clean)}
        clean[t] = r
    ts = sorted(clean)
    if len(ts) < NEEDED:
        return {'status': 'INSUFFICIENT_HISTORY', 'closed_candles': len(ts)}
    last = ts[-NEEDED:]
    if any(b-a != SECONDS for a, b in zip(last, last[1:])):
        return {'status': 'GAPS', 'closed_candles': len(ts)}
    age = now - (last[-1] + SECONDS)
    if age < 0 or age > SECONDS + 300:
        return {'status': 'STALE', 'closed_candles': len(ts), 'age_seconds': age}
    return {'status': 'ELIGIBLE_FOR_FURTHER_VALIDATION', 'closed_candles': len(ts), 'last_candle_id': str(last[-1]), 'last_closed_at_utc': dt.datetime.fromtimestamp(last[-1]+SECONDS, dt.timezone.utc).isoformat(), 'age_seconds': age}


def run():
    result = {'schema_version': '5.4.3', 'generated_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'timeframe': '4h', 'required_closed_candles': NEEDED, 'markets': {}, 'limitations': ['Read-only diagnostic; does not modify the collector or signal engine', 'Exchange identity and volume not independently verified', 'Other timeframes not yet checked', 'No trade authorization']}
    for name, fetch_markets, fetch_candles in [('Kraken Spot', kraken_markets, kraken_candles), ('Gate.io Spot', gate_markets, gate_candles)]:
        try:
            markets = fetch_markets()
        except Exception as exc:
            result['markets'][name] = {'status': 'MARKET_LIST_UNAVAILABLE', 'error': str(exc)[:140], 'pairs': {}}
            continue
        outcomes = {}
        for coin in COINS:
            lookup = f'{coin}/BTC' if name == 'Kraken Spot' else f'{coin}_BTC'
            market = markets.get(lookup)
            if market is None:
                outcomes[coin+'BTC'] = {'status': 'MARKET_NOT_LISTED'}
                continue
            if name == 'Gate.io Spot' and market.get('trade_status') not in (None, 'tradable'):
                outcomes[coin+'BTC'] = {'status': 'MARKET_NOT_TRADABLE'}
                continue
            try:
                market_id = market if name == 'Kraken Spot' else lookup
                outcomes[coin+'BTC'] = assess(fetch_candles(market_id), int(time.time()))
            except Exception as exc:
                outcomes[coin+'BTC'] = {'status': 'FETCH_ERROR', 'error': str(exc)[:140]}
        result['markets'][name] = {'status': 'CHECKED', 'pairs': outcomes}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'sources': {k: v['status'] for k,v in result['markets'].items()}, 'results': {k: {p: x['status'] for p,x in v['pairs'].items()} for k,v in result['markets'].items()}}, ensure_ascii=False))


if __name__ == '__main__':
    run()
