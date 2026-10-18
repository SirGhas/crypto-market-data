#!/usr/bin/env python3
"""Research-only Kraken ZEC/BTC discovery; fail closed; standard library only."""
import datetime as dt
import json
import os
import pathlib
import socket
import sys
import time
import urllib.error
import urllib.request

BASE = 'https://api.kraken.com/0/public/'
OUT = pathlib.Path(os.getenv('KRAKEN_PROBE_OUTPUT', 'artifacts/kraken_pair_probe_v5112.json'))
OUT.parent.mkdir(parents=True, exist_ok=True)

def fetch(endpoint):
    url = BASE + endpoint
    start = time.monotonic()
    rec = {'endpoint': endpoint, 'http_status': None, 'api_errors': [], 'duration_ms': None, 'network_error': None}
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'crypto-market-data-research-probe/5.11.2'})
        with urllib.request.urlopen(req, timeout=18) as rsp:
            rec['http_status'] = rsp.status
            raw = rsp.read(6_000_000)
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get('result'), dict) or not isinstance(data.get('error'), list):
            raise ValueError('Unexpected Kraken JSON schema')
        rec['api_errors'] = data['error']
        return rec, data['result'] if not data['error'] else None
    except urllib.error.HTTPError as exc:
        rec['http_status'] = exc.code
        rec['network_error'] = 'HTTPError: ' + str(exc.reason)[:160]
    except (urllib.error.URLError, TimeoutError, socket.timeout, ValueError, json.JSONDecodeError) as exc:
        rec['network_error'] = type(exc).__name__ + ': ' + str(exc)[:200]
    finally:
        rec['duration_ms'] = round((time.monotonic()-start)*1000)
    return rec, None

stamp = dt.datetime.now(dt.timezone.utc).isoformat()
report = {
    'probe_version': '5.11.2', 'phase': '01_pair_discovery_and_runner_access',
    'timestamp_utc': stamp, 'github': {'repository': os.getenv('GITHUB_REPOSITORY'), 'run_id': os.getenv('GITHUB_RUN_ID'), 'sha': os.getenv('GITHUB_SHA'), 'runner_os': os.getenv('RUNNER_OS')},
    'research_only': True, 'trading_enabled': False, 'signals_enabled': False, 'release_6_0_0_approved': False,
    'endpoint_results': {}, 'matches': [], 'market_exists': None, 'access_verified': False,
    'outcome': 'UNVERIFIED', 'next_phase_authorized': False,
}

pairs_req, pairs = fetch('AssetPairs')
report['endpoint_results']['AssetPairs'] = pairs_req
if pairs is not None:
    report['access_verified'] = True
    for code, info in pairs.items():
        if not isinstance(info, dict):
            continue
        ws = str(info.get('wsname') or '').upper().replace(' ', '')
        alt = str(info.get('altname') or '').upper()
        base = str(info.get('base') or '').upper()
        quote = str(info.get('quote') or '').upper()
        # Match explicit direct pair; do not silently accept a synthetic route.
        direct = (ws in ('ZEC/XBT', 'ZEC/BTC') or alt in ('ZECXBT', 'ZECBTC')
                  or (base == 'ZEC' and quote in ('XXBT', 'XBT', 'BTC')))
        if direct:
            report['matches'].append({'rest_pair_key': code, 'altname': info.get('altname'), 'wsname': info.get('wsname'), 'base': info.get('base'), 'quote': info.get('quote'), 'status': info.get('status'), 'ordermin': info.get('ordermin'), 'costmin': info.get('costmin')})
    report['market_exists'] = bool(report['matches'])
    if not report['matches']:
        report['outcome'] = 'PAIR_NOT_LISTED'
    elif not any(m['status'] in ('online', None) for m in report['matches']):
        report['outcome'] = 'PAIR_LISTED_NOT_ONLINE'
    else:
        report['outcome'] = 'PAIR_LISTED_ACCESS_OK_PENDING_OHLC'
        report['next_phase_authorized'] = True
else:
    report['outcome'] = 'ACCESS_OR_API_ERROR'

# Separate explicit pair lookup helps diagnose symbol mapping, without turning a failure
# into a false absence if the full pair list was unavailable.
pair_req, pair_result = fetch('AssetPairs?pair=ZECXBT')
report['endpoint_results']['AssetPairs_ZECXBT'] = pair_req
report['explicit_lookup_result_keys'] = sorted(pair_result.keys())[:10] if pair_result else []

OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({'outcome': report['outcome'], 'market_exists': report['market_exists'], 'access_verified': report['access_verified'], 'next_phase_authorized': report['next_phase_authorized'], 'output': str(OUT)}, ensure_ascii=False))
# Diagnostic workflows must always upload the report, including blocked outcomes.
sys.exit(0)
