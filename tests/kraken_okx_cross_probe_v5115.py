#!/usr/bin/env python3
"""Research-only Kraken/OKX synthetic ZEC/BTC cross comparison. No trading/signals."""
import datetime as dt
import json
import os
import time
import urllib.parse
import urllib.request
from decimal import Decimal
from pathlib import Path

INTERVALS = {'5m': (5, '5m'), '15m': (15, '15m'), '1h': (60, '1H'), '4h': (240, '4H')}
NOW = int(time.time())
OUTPUT = Path('artifacts/kraken_okx_cross_probe_v5115.json')


def utc(s):
    return dt.datetime.fromtimestamp(int(s), dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def positive(v):
    x = Decimal(str(v))
    if not x.is_finite() or x <= 0:
        raise ValueError('invalid_positive_decimal')
    return x


def request_json(url, params=None):
    full = url + ('?' + urllib.parse.urlencode(params) if params else '')
    meta = {'endpoint': url, 'http_status': None, 'api_code': None, 'api_message': None, 'duration_ms': None, 'network_error': None}
    start = time.monotonic()
    try:
        req = urllib.request.Request(full, headers={'Accept': 'application/json', 'User-Agent': 'crypto-research-cross/5.11.5'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            meta['http_status'] = resp.status
            data = json.loads(resp.read(3_000_000))
        if isinstance(data, dict):
            if 'code' in data: meta['api_code'] = str(data['code'])
            if 'msg' in data: meta['api_message'] = str(data['msg'])[:300]
            if 'error' in data and data['error']: meta['api_message'] = str(data['error'])[:300]
        return data, meta
    except Exception as e:
        meta['network_error'] = f'{type(e).__name__}: {str(e)[:200]}'
        return None, meta
    finally:
        meta['duration_ms'] = round((time.monotonic()-start)*1000)


def kraken_catalog():
    data, meta = request_json('https://api.kraken.com/0/public/AssetPairs')
    if not isinstance(data, dict) or data.get('error') or not isinstance(data.get('result'), dict):
        raise ValueError('kraken_catalog_failed: '+str(meta))
    found = {}
    for asset in ('ZEC', 'BTC'):
        matches = []
        for key, info in data['result'].items():
            if not isinstance(info,dict) or info.get('status') != 'online': continue
            name = str(info.get('wsname','')).upper().replace('XBT','BTC')
            if name == asset+'/USD':
                matches.append({'pair_key':key,'wsname':info.get('wsname'),'status':info.get('status')})
        if len(matches)!=1: raise ValueError('kraken_catalog_ambiguous_'+asset+':'+str(len(matches)))
        found[asset] = matches[0]
    return found, meta


def kraken_rows(pair, minutes):
    data,meta = request_json('https://api.kraken.com/0/public/OHLC', {'pair':pair,'interval':minutes})
    if not isinstance(data,dict) or data.get('error') or not isinstance(data.get('result'),dict):
        raise ValueError('kraken_ohlc_failure: '+str(meta))
    keys=[k for k in data['result'] if k!='last']
    if len(keys)!=1 or not isinstance(data['result'][keys[0]],list): raise ValueError('kraken_ohlc_schema')
    out={}
    for row in data['result'][keys[0]]:
        if not isinstance(row,list) or len(row)<8:continue
        t=int(row[0]); period=minutes*60
        if t+period>NOW:continue
        out[t]={'close':positive(row[4]),'volume_base':str(row[6]),'trades':int(row[7])}
    return out,meta


def okx_rows(symbol,bar,minutes):
    data,meta=request_json('https://www.okx.com/api/v5/market/history-candles', {'instId':symbol,'bar':bar,'limit':100})
    if not isinstance(data,dict) or str(data.get('code'))!='0' or not isinstance(data.get('data'),list):
        raise ValueError('okx_ohlc_failure: '+str(meta))
    out={}
    for row in data['data']:
        if not isinstance(row,list) or len(row)<9:continue
        t=int(row[0])//1000
        if str(row[8])!='1' or t+minutes*60>NOW:continue
        out[t]={'close':positive(row[4]),'volume_base':str(row[5])}
    return out,meta


def cross(z,b,minutes):
    common=sorted(set(z)&set(b))
    if not common:return {'status':'NO_COMMON_CLOSED_CANDLE', 'fresh':False}
    t=common[-1]; period=minutes*60; age=NOW-(t+period)
    fresh=0<=age<=period+120
    ratio=z[t]['close']/b[t]['close']
    return {'status':'FRESH_ALIGNED' if fresh else 'STALE_ALIGNED', 'start_epoch':t,
            'start_utc':utc(t),'end_utc':utc(t+period),'age_after_close_seconds':age,
            'aligned_candle_count':len(common),'zec_close':str(z[t]['close']),
            'btc_close':str(b[t]['close']),'synthetic_zec_btc':format(ratio,'.12f'),
            'zec_native_volume':z[t]['volume_base'],'btc_native_volume':b[t]['volume_base'],
            'synthetic_volume':None,'synthetic_liquidity':None,
            'fresh':fresh,'identity':f'{t}:{minutes}'}


def main():
    doc={'probe_version':'5.11.5','phase':'02b_okx_parameter_fix_cross_comparison',
         'timestamp_utc':utc(NOW), 'github':{'repository':os.getenv('GITHUB_REPOSITORY'),
         'run_id':os.getenv('GITHUB_RUN_ID'),'sha':os.getenv('GITHUB_SHA'),'runner_os':os.getenv('RUNNER_OS')},
         'research_only':True,'trading_enabled':False,'signals_enabled':False,
         'exchange_admission_authorized':False,'synthetic_signal_authorized':False,
         'release_6_0_0_approved':False,'timeframe_mapping':{k:v[1] for k,v in INTERVALS.items()},
         'usd_usdt_basis_caveat':'USD versus USDT mismatch; divergence diagnostic only',
         'intervals':{}, 'errors':[], 'outcome':'RESEARCH_SNAPSHOT_ONLY'}
    pairs={}
    try:
        pairs, catalog_meta=kraken_catalog()
        doc['kraken_catalog_endpoint']=catalog_meta
    except Exception as e:doc['errors'].append(str(e))
    doc['kraken_discovered_pairs']=pairs
    for label,(minutes,bar) in INTERVALS.items():
        entry={'kraken':None,'okx_reference':None,'divergence_percent':None,
               'diagnostic_eligible':False,'errors':[], 'endpoint_results':{}}
        doc['intervals'][label]=entry
        if len(pairs)==2:
            for asset in ('ZEC','BTC'):
                try:
                    rows,meta=kraken_rows(pairs[asset]['pair_key'], minutes)
                    entry['endpoint_results']['kraken_'+asset.lower()]=meta
                    entry.setdefault('_kraken_rows',{})[asset]=rows
                except Exception as e:entry['errors'].append('KRAKEN_'+asset+': '+str(e))
            if len(entry.get('_kraken_rows',{}))==2:
                entry['kraken']=cross(entry['_kraken_rows']['ZEC'],entry['_kraken_rows']['BTC'],minutes)
            entry.pop('_kraken_rows',None)
        else:entry['errors'].append('KRAKEN_PAIRS_UNVERIFIED')
        for asset in ('ZEC','BTC'):
            try:
                rows,meta=okx_rows(asset+'-USDT',bar,minutes)
                entry['endpoint_results']['okx_'+asset.lower()]=meta
                entry.setdefault('_okx_rows',{})[asset]=rows
            except Exception as e:entry['errors'].append('OKX_'+asset+': '+str(e))
        if len(entry.get('_okx_rows',{}))==2:
            entry['okx_reference']=cross(entry['_okx_rows']['ZEC'],entry['_okx_rows']['BTC'],minutes)
        entry.pop('_okx_rows',None)
        k,o=entry['kraken'],entry['okx_reference']
        if k and o and k.get('fresh') and o.get('fresh') and k['start_epoch']==o['start_epoch']:
            entry['divergence_percent']=format((Decimal(k['synthetic_zec_btc'])/Decimal(o['synthetic_zec_btc'])-1)*100,'.6f')
            entry['diagnostic_eligible']=True
        elif k and o and k.get('start_epoch')!=o.get('start_epoch'):
            entry['errors'].append('CROSS_EXCHANGE_CANDLE_TIME_MISMATCH')
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Wrote',OUTPUT,'eligible:',{k:v['diagnostic_eligible'] for k,v in doc['intervals'].items()})

if __name__=='__main__':main()
