"""Read-only ZEC market-feed audit; never promotes fallback/derived crosses."""
import argparse
import datetime as dt
import json
import time
from pathlib import Path

FRAMES = {'5m':300,'15m':900,'1h':3600,'4h':14400}
SYMBOLS = ('ZECUSDT','ZECBTC')
MIN_CANDLES = 233

def inspect(market, now=None, prior=None):
    now = time.time() if now is None else now
    result = {'schema_version':'5.10.0','mode':'research_only_no_orders_no_push',
              'generated_at_utc':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),
              'feeds':{},'release_6_0_0_approved':False,
              'limitations':['Two immediate runs may share the same last closed candle; unchanged does not imply stale.',
                             'A single run cannot prove cross-run freshness; use later runs across candle boundaries.',
                             'Cross validation requires independent price parity and liquidity checks before publication.']}
    for symbol in SYMBOLS:
        result['feeds'][symbol]={}
        for tf,sec in FRAMES.items():
            f=market.get('pairs',{}).get(symbol,{}).get('frames',{}).get(tf,{})
            errors=[]; source=f.get('source'); candles=f.get('candles')
            if f.get('status')!='available': errors.append('not_available')
            if source!='OKX Spot': errors.append('not_verified_primary_okx')
            if not isinstance(candles,list) or len(candles)<MIN_CANDLES: errors.append('insufficient_history')
            stamps=[]; last=None; age=None; changed=None; previous=None
            if isinstance(candles,list) and candles:
                try:
                    stamps=[int(c['t']) for c in candles]
                    if any(b-a!=sec for a,b in zip(stamps,stamps[1:])): errors.append('noncontiguous_candles')
                    if any(not all(k in c for k in ('o','h','l','c','v')) for c in candles): errors.append('missing_ohlcv')
                    last=stamps[-1]+sec
                    age=round(now-last,2)
                    if not 0<=age<=sec+300: errors.append('stale_or_future_candle')
                except (ValueError,TypeError,KeyError,OverflowError): errors.append('malformed_candles')
            if prior is not None:
                previous=prior.get('feeds',{}).get(symbol,{}).get(tf,{}).get('last_closed_end_unix')
                if previous is not None and last is not None:
                    changed=last>previous
                    if last<previous: errors.append('candle_regression')
                    # Do not mark unchanged as stale until a newer close is due.
                    if last==previous and now>last+sec+300: errors.append('no_advance_after_deadline')
            result['feeds'][symbol][tf]={
                'status':'PASS_SOURCE_AND_FRESHNESS' if not errors else 'BLOCK_UNVERIFIED',
                'source':source,'reported_status':f.get('status'),'candle_count':len(candles) if isinstance(candles,list) else 0,
                'last_closed_end_unix':last,'last_closed_end_utc':dt.datetime.fromtimestamp(last,dt.timezone.utc).isoformat() if last is not None else None,
                'age_seconds':age,'previous_closed_end_unix':previous,'advanced_since_previous':changed,
                'errors':errors}
    allfeeds=[f for v in result['feeds'].values() for f in v.values()]
    result['summary']={'attempted_feeds':len(allfeeds),'passed_feeds':sum(f['status']=='PASS_SOURCE_AND_FRESHNESS' for f in allfeeds),
                       'blocked_feeds':sum(f['status']!='PASS_SOURCE_AND_FRESHNESS' for f in allfeeds),
                       'zec_btc_4h_source_verified':result['feeds']['ZECBTC']['4h']['status']=='PASS_SOURCE_AND_FRESHNESS',
                       'cross_run_advance_proven':any(f['advanced_since_previous'] is True for f in allfeeds),
                       'publication_approved':False}
    result['status']='PASS_AUDIT_COMPLETED' # Audit ran, NOT proof all feeds passed.
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--market',default='data/multisource_market.json');p.add_argument('--previous');p.add_argument('--output',default='data/zec_feed_audit_v5100.json');a=p.parse_args()
    market=json.loads(Path(a.market).read_text(encoding='utf-8'))
    prior=json.loads(Path(a.previous).read_text(encoding='utf-8')) if a.previous and Path(a.previous).exists() else None
    out=inspect(market,prior=prior)
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'summary':out['summary'],'blocked_details':{s:{tf:f['errors'] for tf,f in fs.items() if f['errors']} for s,fs in out['feeds'].items()}},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
