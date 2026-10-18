#!/usr/bin/env python3
"""Research-only Kraken ZEC/USD÷BTC/USD versus independent OKX ZEC/USDT÷BTC/USDT.
No orders, trading actions, signals, or release authorization.
"""
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path

INTERVALS = {"5m": (5, 5), "15m": (15, 15), "1h": (60, 60), "4h": (240, 240)}
NOW = int(time.time())
OUTPUT = Path('artifacts/kraken_synthetic_probe_v5114.json')

def utc(sec):
    return dt.datetime.fromtimestamp(int(sec), dt.timezone.utc).isoformat().replace('+00:00', 'Z')

def dec(v):
    n = Decimal(str(v))
    if not n.is_finite() or n <= 0:
        raise ValueError('nonpositive_or_nonfinite_price')
    return n

def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent':'CryptoDataResearchProbe/5.11.4', 'Accept':'application/json'})
    start = time.monotonic()
    out = {'url':url.split('?')[0], 'http_status':None, 'duration_ms':None, 'errors':[]}
    try:
        with urllib.request.urlopen(request,timeout=18) as response:
            out['http_status'] = response.status
            raw = response.read(3_000_000)
        data = json.loads(raw)
    except Exception as exc:
        out['errors'] = [f'{type(exc).__name__}: {str(exc)[:180]}']
        data = None
    out['duration_ms'] = round((time.monotonic()-start)*1000)
    return data,out

def kraken_pair(base):
    # Discover from the full pair listing, rather than assume Kraken's historical ticker encoding.
    data, meta = fetch('https://api.kraken.com/0/public/AssetPairs')
    if not isinstance(data,dict) or data.get('error') or not isinstance(data.get('result'),dict):
        raise ValueError('kraken_pair_catalog_unavailable: '+str(meta['errors'] or (data or {}).get('error')))
    matches=[]
    for key,item in data['result'].items():
        if not isinstance(item,dict):continue
        ws=str(item.get('wsname','')).upper().replace('XBT','BTC')
        alt=str(item.get('altname','')).upper()
        if ws == base+'/USD' and item.get('status','online') == 'online':
            matches.append({'key':key,'altname':alt,'wsname':item.get('wsname'),'status':item.get('status','unknown')})
    if len(matches)!=1:
        raise ValueError('expected_exactly_one_online_'+base+'_USD_pair_found_'+str(len(matches)))
    return matches[0]

def kraken_candles(pair,interval):
    q=urllib.parse.urlencode({'pair':pair['key'],'interval':interval})
    data,meta=fetch('https://api.kraken.com/0/public/OHLC?'+q)
    if not isinstance(data,dict) or data.get('error') or not isinstance(data.get('result'),dict):
        raise ValueError('kraken_ohlc_invalid: '+str(meta['errors'] or (data or {}).get('error')))
    result=data['result']; keys=[key for key in result if key!='last']
    if len(keys)!=1 or not isinstance(result[keys[0]],list):raise ValueError('kraken_ohlc_result_invalid')
    rows={}
    for item in result[keys[0]]:
        if not isinstance(item,list) or len(item)<8:continue
        t=int(item[0]);
        if t+interval*60>NOW:continue # reject current uncommitted candle
        rows[t]={'start':t,'close':dec(item[4]),'volume_base':str(item[6]),'trades':int(item[7])}
    return rows,meta

def okx_candles(symbol,bar):
    q=urllib.parse.urlencode({'instId':symbol,'bar':bar,'limit': '100'})
    data,meta=fetch('https://www.okx.com/api/v5/market/history-candles?'+q)
    if not isinstance(data,dict) or str(data.get('code'))!='0' or not isinstance(data.get('data'),list):
        raise ValueError('okx_ohlc_invalid: '+str(meta['errors'] or (data or {}).get('msg')))
    rows={}
    for item in data['data']:
        if not isinstance(item,list) or len(item)<9:continue
        t=int(item[0])//1000
        if str(item[8])!='1' or t+bar*60>NOW:continue
        rows[t]={'start':t,'close':dec(item[4]),'volume_base':str(item[5])}
    return rows,meta

def snapshot_pair(rows1,rows2,period):
    common=sorted(set(rows1)&set(rows2))
    if not common:return {'status':'NO_ALIGNED_CLOSED_CANDLES'}
    t=common[-1]; age=NOW-(t+period*60)
    # A full extra period may pass in quiet markets; do not promote it as fresh.
    fresh=0<=age<=period*60+120
    a,b=rows1[t],rows2[t]
    rate=a['close']/b['close']
    return {'status':'FRESH_ALIGNED' if fresh else 'STALE_ALIGNED',
            'start_utc':utc(t),'start_epoch':t,'end_utc':utc(t+period*60),
            'age_after_close_seconds':age,'aligned_candle_count':len(common),
            'base_close':str(a['close']),'quote_close':str(b['close']),
            'synthetic_zec_btc':format(rate,'.12f'),
            'base_volume_is_native':True,'quote_volume_is_native':True,
            'synthetic_volume':None,'synthetic_liquidity':None,'fresh':fresh,
            'identity':str(t)+':'+str(period)}

def main():
    result={'probe_version':'5.11.4','phase':'02_synthetic_cross_research','timestamp_utc':utc(NOW),
            'github':{'repository':os.getenv('GITHUB_REPOSITORY'),'run_id':os.getenv('GITHUB_RUN_ID'),'sha':os.getenv('GITHUB_SHA'),'runner_os':os.getenv('RUNNER_OS')},
            'research_only':True,'trading_enabled':False,'signals_enabled':False,'release_6_0_0_approved':False,
            'exchange_admission_authorized':False,'synthetic_signal_authorized':False,
            'method':'Kraken ZEC/USD divided by Kraken BTC/USD; independent reference OKX ZEC/USDT divided by OKX BTC/USDT',
            'usd_usdt_basis_caveat':'Prices are NOT in identical fiat quote currencies; divergence is diagnostic, not an exact arbitrage spread.',
            'intervals':{},'errors':[]}
    pairs={}
    for asset in ('ZEC','BTC'):
        try:pairs[asset]=kraken_pair(asset)
        except Exception as exc:result['errors'].append(str(exc))
    result['kraken_discovered_usd_pairs']=pairs
    for name,(kraken_interval,okx_interval) in INTERVALS.items():
        entry={'kraken':None,'okx_reference':None,'divergence_percent':None,'diagnostic_eligible':False,'errors':[], 'endpoint_results':{}}
        result['intervals'][name]=entry
        if len(pairs)!=2:
            entry['errors'].append('MISSING_VERIFIED_KRAKEN_PAIR');continue
        try:
            z,mz=kraken_candles(pairs['ZEC'],kraken_interval)
            b,mb=kraken_candles(pairs['BTC'],kraken_interval)
            entry['endpoint_results']['kraken_zec']=mz;entry['endpoint_results']['kraken_btc']=mb
            entry['kraken']=snapshot_pair(z,b,kraken_interval)
        except Exception as exc:entry['errors'].append('KRAKEN: '+str(exc))
        try:
            z,mz=okx_candles('ZEC-USDT',okx_interval)
            b,mb=okx_candles('BTC-USDT',okx_interval)
            entry['endpoint_results']['okx_zec']=mz;entry['endpoint_results']['okx_btc']=mb
            entry['okx_reference']=snapshot_pair(z,b,okx_interval)
        except Exception as exc:entry['errors'].append('OKX: '+str(exc))
        a=entry['kraken'];b=entry['okx_reference']
        if a and b and a.get('fresh') and b.get('fresh'):
            # Compare ONLY the same candle period, not merely the latest from each provider.
            if a['start_epoch']==b['start_epoch']:
                entry['divergence_percent']=format((Decimal(a['synthetic_zec_btc'])/Decimal(b['synthetic_zec_btc'])-1)*100,'.5f')
                entry['diagnostic_eligible']=True
            else:entry['errors'].append('CROSS_EXCHANGE_CANDLE_TIME_MISMATCH')
    result['outcome']='RESEARCH_SNAPSHOT_ONLY'
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Saved',OUTPUT, 'intervals:', [(k,v['diagnostic_eligible'],v['errors']) for k,v in result['intervals'].items()])
    return 0

if __name__=='__main__':raise SystemExit(main())
