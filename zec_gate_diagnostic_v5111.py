"""Read-only Gate.io Spot symbol/error diagnostic. No approvals, trades or secrets."""
import datetime as dt
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = 'https://api.gateio.ws/api/v4/spot'
HEADERS = {'Accept': 'application/json', 'User-Agent': 'zec-research-diagnostic/5.11.1'}


def compact_body(raw):
    """Return a bounded response body; never include request headers or credentials."""
    text = raw[:1600].decode('utf-8', errors='replace')
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return {'label': str(obj.get('label', ''))[:100],
                    'message': str(obj.get('message', ''))[:500]}
        return {'body_excerpt': text[:500]}
    except (ValueError, TypeError):
        return {'body_excerpt': text[:500]}


def request(path, params=None, opener=urllib.request.urlopen):
    url = BASE + path + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with opener(req, timeout=18) as response:
            raw = response.read(2_000_000)
            parsed = json.loads(raw)
            return {'http_status': response.status, 'ok': True}, parsed
    except urllib.error.HTTPError as exc:
        with exc:
            raw = exc.read(1600)
        return {'http_status': exc.code, 'ok': False, 'error_response': compact_body(raw)}, None
    except Exception as exc:
        return {'http_status': None, 'ok': False,
                'error_type': type(exc).__name__, 'error_message': str(exc)[:250]}, None


def run(fetch=request):
    out = {'schema_version': '5.11.1', 'mode': 'READ_ONLY_DIAGNOSTIC',
           'generated_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
           'tests': {}, 'listed_zec_pairs': [], 'publication_approved': False,
           'gate_fallback_approved': False, 'release_6_0_0_approved': False}
    # Positive control distinguishes unsupported ZEC_BTC from general API/network failure.
    for pair in ('BTC_USDT', 'ZEC_USDT', 'ZEC_BTC'):
        market_status, market = fetch('/currency_pairs/' + pair)
        ticker_status, ticker = fetch('/tickers', {'currency_pair': pair})
        candle_status, candles = fetch('/candlesticks', {'currency_pair': pair, 'interval': '1h', 'limit': 3})
        out['tests'][pair] = {
            'market': {**market_status, 'trade_status': market.get('trade_status') if isinstance(market, dict) else None,
                       'base': market.get('base') if isinstance(market, dict) else None,
                       'quote': market.get('quote') if isinstance(market, dict) else None},
            'ticker': {**ticker_status, 'returned_items': len(ticker) if isinstance(ticker, list) else None},
            'candles_1h': {**candle_status, 'returned_items': len(candles) if isinstance(candles, list) else None},
        }
    listing_status, listing = fetch('/currency_pairs')
    if listing_status['ok'] and isinstance(listing, list):
        out['listed_zec_pairs'] = sorted(str(p.get('id')) for p in listing
                                         if isinstance(p, dict) and
                                         (p.get('base') == 'ZEC' or p.get('quote') == 'ZEC'))[:100]
    out['listing'] = {**listing_status, 'total_pairs': len(listing) if isinstance(listing, list) else None}
    control_ok = out['tests']['BTC_USDT']['market']['ok']
    target_ok = out['tests']['ZEC_BTC']['market']['ok']
    out['diagnosis'] = ('TARGET_MARKET_DISCOVERED_NEEDS_FULL_AUDIT' if target_ok else
                        'TARGET_REJECTED_WHILE_CONTROL_WORKS' if control_ok else
                        'INCONCLUSIVE_CONTROL_FAILED')
    out['status'] = 'DIAGNOSTIC_COMPLETE_NO_PROMOTION'
    return out


def main():
    result = run()
    dest = Path('data/zec_gate_diagnostic_v5111.json')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
