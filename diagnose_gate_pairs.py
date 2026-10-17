"""Read-only Gate.io Spot market diagnostics; no orders, no changes to market data."""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PAIRS = ('AAVE_BTC', 'AVAX_BTC', 'LINK_BTC', 'SUI_BTC', 'BNB_BTC', 'XRP_BTC')
BASE = 'https://api.gateio.ws/api/v4/spot'
OUT = Path('data/gate_pair_diagnostics.json')

def request(path, params=None):
    url = BASE + path + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'crypto-market-research/5.5.1'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            body = response.read(8192).decode('utf-8', 'replace')
            return {'http_status': response.status, 'body': json.loads(body)}
    except urllib.error.HTTPError as exc:
        return {'http_status': exc.code, 'body': exc.read(2048).decode('utf-8', 'replace')}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {'http_status': None, 'error': str(exc)}

def main():
    report = {'schema_version': '5.5.1', 'generated_at_utc': datetime.now(timezone.utc).isoformat(), 'source': 'Gate.io Spot', 'pairs': {}}
    for pair in PAIRS:
        market = request('/currency_pairs/' + pair)
        candles = request('/candlesticks', {'currency_pair': pair, 'interval': '5m', 'limit': 3})
        rows = candles.get('body')
        report['pairs'][pair] = {
            'market_http_status': market.get('http_status'),
            'market_details': market.get('body') if market.get('http_status') != 200 else {
                k: market['body'].get(k) for k in ('id', 'trade_status', 'base', 'quote', 'min_base_amount', 'min_quote_amount')
            },
            'candles_http_status': candles.get('http_status'),
            'candles_count': len(rows) if isinstance(rows, list) else None,
            'candles_error': None if isinstance(rows, list) else candles.get('body', candles.get('error')),
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(OUT), 'market_status': {k: v['market_http_status'] for k, v in report['pairs'].items()}}))

if __name__ == '__main__':
    main()
