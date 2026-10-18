"""Read-only Gate ZEC_BTC discovery. Does NOT approve a fallback or publication."""
import argparse
import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE='https://api.gateio.ws/api/v4/spot'
FRAMES={'5m':300,'15m':900,'1h':3600,'4h':14400}
INTERVALS={'5m':'5m','15m':'15m','1h':'1h','4h':'4h'}

def request_json(path,params=None):
    url=BASE+path+('?' + urllib.parse.urlencode(params) if params else '')
    req=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':'zec-research-audit/5.11.0'})
    with urllib.request.urlopen(req,timeout=18) as response:
        return json.load(response)

def number(v):
    try: return float(v)
    except (TypeError,ValueError,OverflowError): return None

def inspect_candles(raw,sec,now):
    # Gate v4 spot candles: [timestamp, quote_volume, close, high, low, open, base_volume, ...]
    if not isinstance(raw,list): return {'status':'BLOCK','reason':'non_list_response'}
    parsed=[]
    for c in raw:
        if not isinstance(c,list) or len(c)<7: return {'status':'BLOCK','reason':'malformed_candle'}
        try: t=int(c[0])
        except (ValueError,TypeError): return {'status':'BLOCK','reason':'invalid_timestamp'}
        vals=[number(c[i]) for i in (2,3,4,5,6)]
        if any(x is None or x<0 for x in vals): return {'status':'BLOCK','reason':'invalid_ohlcv'}
        parsed.append((t,vals))
    parsed.sort(key=lambda x:x[0]); parsed=[x for x in parsed if x[0]+sec<=now]
    if len(parsed)<233: return {'status':'BLOCK','reason':'insufficient_closed_history','closed_candles':len(parsed)}
    stamps=[x[0] for x in parsed]
    if len(set(stamps))!=len(stamps) or any(b-a!=sec for a,b in zip(stamps,stamps[1:])):
        return {'status':'BLOCK','reason':'noncontiguous_history','closed_candles':len(parsed)}
    last=stamps[-1]+sec; age=now-last
    if not 0<=age<=sec+300: return {'status':'BLOCK','reason':'stale_closed_candle','age_seconds':round(age,1)}
    return {'status':'PASS_CANDLES_ONLY','closed_candles':len(parsed),'last_closed_end_utc':dt.datetime.fromtimestamp(last,dt.timezone.utc).isoformat(),'last_closed_end_unix':last,'age_seconds':round(age,1),'last_close':parsed[-1][1][0]}

def probe(fetch=request_json,now=None):
    now=time.time() if now is None else now
    out={'schema_version':'5.11.0','mode':'RESEARCH_ONLY_NO_PROMOTION','generated_at_utc':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),
         'pair':'ZEC_BTC','exchange':'Gate.io Spot','checks':{},'frames':{},'publication_approved':False,'gate_fallback_approved':False,'release_6_0_0_approved':False}
    try:
        pair=fetch('/currency_pairs/ZEC_BTC')
        if not isinstance(pair,dict): raise ValueError('unexpected pair metadata')
        status=str(pair.get('trade_status','')).lower()
        out['checks']['market']={'status':'PASS_DISCOVERY_ONLY' if status=='tradable' else 'BLOCK','trade_status':status,'base':pair.get('base'),'quote':pair.get('quote'),'min_base_amount':pair.get('min_base_amount'),'min_quote_amount':pair.get('min_quote_amount')}
    except Exception as e:
        out['checks']['market']={'status':'BLOCK','error':type(e).__name__+': '+str(e)[:180]}
    try:
        tick=fetch('/tickers',{'currency_pair':'ZEC_BTC'})
        tick=tick[0] if isinstance(tick,list) and tick else {}
        if not isinstance(tick,dict): tick={}
        last=number(tick.get('last')); vol=number(tick.get('quote_volume'))
        out['checks']['ticker']={'status':'PASS_OBSERVATION_ONLY' if last and last>0 and vol is not None and vol>0 else 'BLOCK','last_btc':last,'quote_volume_btc_24h':vol}
    except Exception as e: out['checks']['ticker']={'status':'BLOCK','error':type(e).__name__+': '+str(e)[:180]}
    try:
        book=fetch('/order_book',{'currency_pair':'ZEC_BTC','limit':20})
        bids=book.get('bids',[]) if isinstance(book,dict) else [];asks=book.get('asks',[]) if isinstance(book,dict) else []
        bid=number(bids[0][0]) if bids else None;ask=number(asks[0][0]) if asks else None
        spread=10000*(ask-bid)/((ask+bid)/2) if bid and ask and 0<bid<=ask else None
        # Snapshot only; no assumption that this proves execution liquidity.
        out['checks']['order_book']={'status':'PASS_SNAPSHOT_ONLY' if spread is not None else 'BLOCK','best_bid_btc':bid,'best_ask_btc':ask,'spread_bps':round(spread,3) if spread is not None else None,'bid_levels':len(bids),'ask_levels':len(asks)}
    except Exception as e: out['checks']['order_book']={'status':'BLOCK','error':type(e).__name__+': '+str(e)[:180]}
    for tf,sec in FRAMES.items():
        try: out['frames'][tf]=inspect_candles(fetch('/candlesticks',{'currency_pair':'ZEC_BTC','interval':INTERVALS[tf],'limit':250}),sec,now)
        except Exception as e: out['frames'][tf]={'status':'BLOCK','error':type(e).__name__+': '+str(e)[:180]}
    out['summary']={'market_discovered':out['checks'].get('market',{}).get('status')=='PASS_DISCOVERY_ONLY',
                    'closed_candle_frames_passed':sum(f.get('status')=='PASS_CANDLES_ONLY' for f in out['frames'].values()),
                    'independent_price_parity_verified':False,'execution_liquidity_verified':False,'cross_run_freshness_verified':False,
                    'publication_approved':False}
    out['status']='AUDIT_COMPLETED_NOT_APPROVED'
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='data/zec_gate_probe_v5110.json');args=p.parse_args()
    out=probe();dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(out,indent=2,ensure_ascii=False))

if __name__=='__main__': main()
