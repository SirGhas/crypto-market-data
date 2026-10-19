"""Read-only experimental OHLCV reaction/zone volume and order-book evidence.
No trading recommendation. Snapshot history is observed, never backfilled or inferred.
"""
from __future__ import annotations
import json, time, urllib.request, urllib.parse, urllib.error, hashlib
from decimal import Decimal as D, InvalidOperation
from copy import deepcopy

VERSION='alpha-1.6.1-observed-evidence-research'
BASE='https://www.okx.com/api/v5/market/'


def dec(x):
    try:
        y=D(str(x)); return y if y.is_finite() else None
    except (TypeError,ValueError,InvalidOperation): return None


def fmt(x): return format(x.quantize(D('0.00000001')).normalize(),'f')


def okx(endpoint, args, transport=None):
    url=BASE+endpoint+'?'+urllib.parse.urlencode(args)
    if transport is not None: obj=transport(url)
    else:
        req=urllib.request.Request(url,headers={'User-Agent':'alpha-v161-observed-evidence/1.0','Accept':'application/json'})
        with urllib.request.urlopen(req,timeout=18) as res: obj=json.load(res)
    if not isinstance(obj,dict) or obj.get('code')!='0' or not isinstance(obj.get('data'),list):
        raise ValueError('EXCHANGE_RESPONSE_INVALID')
    return obj['data']


def closed_volume_candles(asset,bar,expected,close,transport=None):
    rows=okx('candles',{'instId':asset+'-USDT','bar':bar,'limit':'100'},transport)
    seen=set(); parsed=[]
    for r in rows:
        if not isinstance(r,list) or len(r)<9 or str(r[8])!='1':continue
        ts=int(r[0])//1000
        if ts in seen:raise ValueError('DUPLICATE_VOLUME_CANDLE')
        seen.add(ts)
        o,h,l,c,v=(dec(r[i]) for i in (1,2,3,4,5))
        if any(x is None for x in (o,h,l,c,v)) or min(o,h,l,c)<=0 or v<0 or l>min(o,c) or h<max(o,c):
            raise ValueError('INVALID_VOLUME_CANDLE')
        parsed.append((ts,o,h,l,c,v))
    parsed.sort()
    parsed=[r for r in parsed if r[0]<=expected]
    duration=14400 if bar=='4H' else 86400
    if len(parsed)<40 or parsed[-1][0]!=expected or parsed[-1][4]!=dec(close):
        raise ValueError('VOLUME_HISTORY_IDENTITY_OR_PRICE_MISMATCH')
    if any(b[0]-a[0]!=duration for a,b in zip(parsed,parsed[1:])):
        raise ValueError('GAPPED_VOLUME_HISTORY')
    return parsed


def reaction_evidence(zone,history,atr,tolerance):
    """Chronologically count independent, causal local rejection observations.
    Confirm rebound on the next 2 *closed* bars; excludes unconfirmed last bars.
    """
    lower,upper=dec(zone['low']),dec(zone['high'])
    side=zone['side']; events=[];last_i=-10
    for i in range(20,len(history)-2):
        ts,o,h,l,c,v=history[i]
        if i-last_i<4:continue
        near=(l<=upper+tolerance and h>=lower-tolerance)
        if not near:continue
        before=sum(r[5] for r in history[i-20:i])/D(20)
        ratio=v/before if before>0 else None
        future=history[i+1:i+3]
        if side=='support':
            # Close in or above zone, then enough price response above zone after touch.
            amplitude=max(x[2] for x in future)-l
            confirmed=(c>=lower and amplitude>=atr*D('0.3'))
        else:
            amplitude=h-min(x[3] for x in future)
            confirmed=(c<=upper and amplitude>=atr*D('0.3'))
        if confirmed:
            events.append({'candle_start_epoch':ts,'volume_rvol20':fmt(ratio) if ratio is not None else None,
                           'response_atr_multiple':fmt(amplitude/atr) if atr>0 else None})
            last_i=i
    ratios=[dec(e['volume_rvol20']) for e in events if e['volume_rvol20'] is not None]
    return {'independent_confirmed_observations':len(events),'events':events[-6:],
            'mean_observation_rvol20':fmt(sum(ratios)/len(ratios)) if ratios else None,
            'evidence_definition':'touch and directional response in next 2 closed candles; >=0.3 ATR; >=4 bars apart',
            'limitations':['OBSERVATIONAL_NOT_CAUSAL_PROOF','OHLCV_BAR_VOLUME_NOT_TRADE_BY_PRICE']}


def book_sample(asset,transport=None,now_ms=None):
    rows=okx('books',{'instId':asset+'-USDT','sz':'50'},transport)
    if len(rows)!=1 or not isinstance(rows[0],dict):raise ValueError('BOOK_RESPONSE_INVALID')
    data=rows[0]; bids=data.get('bids',[]);asks=data.get('asks',[])
    if not bids or not asks:raise ValueError('EMPTY_BOOK')
    def parse(levels,rev):
        out=[]
        for level in levels:
            if len(level)<2:raise ValueError('INVALID_BOOK_LEVEL')
            p,s=dec(level[0]),dec(level[1])
            if p is None or s is None or p<=0 or s<0:raise ValueError('INVALID_BOOK_LEVEL')
            out.append((p,s))
        if any((a[0]<=b[0] if rev else a[0]>=b[0]) for a,b in zip(out,out[1:])):
            raise ValueError('UNSORTED_BOOK')
        return out
    b=parse(bids,True);a=parse(asks,False)
    if b[0][0]>=a[0][0]:raise ValueError('CROSSED_BOOK')
    exchange_ts=int(data.get('ts') or 0)
    observed_ms=int(now_ms if now_ms is not None else time.time()*1000)
    if exchange_ts<=0 or exchange_ts>observed_ms+10000 or observed_ms-exchange_ts>120000:
        raise ValueError('STALE_OR_FUTURE_BOOK')
    mid=(b[0][0]+a[0][0])/2
    band=mid*D('0.01')
    bid_notional=sum(p*s for p,s in b if p>=mid-band)
    ask_notional=sum(p*s for p,s in a if p<=mid+band)
    imbalance=(bid_notional-ask_notional)/(bid_notional+ask_notional) if bid_notional+ask_notional>0 else None
    return {'exchange_timestamp_ms':exchange_ts,'observed_timestamp_ms':observed_ms,
            'best_bid':fmt(b[0][0]),'best_ask':fmt(a[0][0]),
            'spread_bps':fmt((a[0][0]-b[0][0])/mid*D(10000)),
            'bid_notional_1pct_usdt':fmt(bid_notional),'ask_notional_1pct_usdt':fmt(ask_notional),
            'imbalance_1pct':fmt(imbalance) if imbalance is not None else None,
            'book_depth_levels':{'bid':len(b),'ask':len(a)},
            'book_sample_type':'OBSERVED_TOP_50_LEVELS_NOT_FULL_DEPTH'}


def check_book_series(samples, min_gap_ms=1000):
    if len(samples)<3:raise ValueError('INSUFFICIENT_BOOK_SNAPSHOTS')
    ss=sorted(samples,key=lambda s:s['observed_timestamp_ms'])
    if any(int(y['observed_timestamp_ms'])-int(x['observed_timestamp_ms'])<min_gap_ms for x,y in zip(ss,ss[1:])):
        raise ValueError('BOOK_SAMPLES_TOO_CLOSE')
    if any(int(y['exchange_timestamp_ms'])<int(x['exchange_timestamp_ms']) for x,y in zip(ss,ss[1:])):
        raise ValueError('BOOK_EXCHANGE_TIME_REGRESSION')
    vals=[dec(s['imbalance_1pct']) for s in ss]
    spreads=[dec(s['spread_bps']) for s in ss]
    if any(v is None for v in vals+spreads):raise ValueError('INVALID_BOOK_SERIES')
    return {'sample_count':len(ss),'time_span_seconds':fmt(D(ss[-1]['observed_timestamp_ms']-ss[0]['observed_timestamp_ms'])/1000),
            'mean_imbalance_1pct':fmt(sum(vals)/len(vals)),
            'maximum_spread_bps':fmt(max(spreads)),
            'direction_consistent':all(v>0 for v in vals) or all(v<0 for v in vals),
            'history_scope':'ONLY_ACTUALLY_OBSERVED_SAMPLES',
            'not_historical_backfill':True}


def evidence_overlay(report, histories, books):
    if report.get('version')!='alpha-1.6-multitimeframe-level-quality-research':
        raise ValueError('EXPECTED_V16_REPORT')
    result=deepcopy(report);result['version']=VERSION;result['evidence_v161']={}
    for asset,item in sorted(result.get('assets',{}).items()):
        level=item.get('level_quality_v16',{})
        ev={'status':'RESEARCH_EVIDENCE_PARTIAL','reaction_zones':[],
            'order_book':books.get(asset,{'status':'UNAVAILABLE'}),
            'blocking_reasons':[], 'trade_authorized':False,'signals_authorized':False}
        for tf in ('4h','1D'):
            if tf not in histories.get(asset,{}):ev['blocking_reasons'].append('NO_VALIDATED_OHLCV_'+tf)
        if level.get('status')!='PARTIAL_LEVEL_QUALITY_RESEARCH':
            ev['blocking_reasons'].append('V16_ZONES_NOT_VALIDATED')
        if not ev['blocking_reasons']:
            atr=dec(level.get('data_validation',{}).get('atr14_4h'))
            tol=dec(level.get('data_validation',{}).get('zone_tolerance'))
            if not atr or not tol:ev['blocking_reasons'].append('INVALID_ZONE_ATR')
            else:
                for z in level.get('zones',[]):
                    combined={}
                    for tf in ('4h','1D'):
                        combined[tf]=reaction_evidence(z,histories[asset][tf],atr,tol)
                    ev['reaction_zones'].append({'side':z['side'],'low':z['low'],'high':z['high'],
                       'multi_timeframe_reaction_evidence':combined})
        if isinstance(ev['order_book'],dict) and ev['order_book'].get('status')!='OBSERVED':
            ev['blocking_reasons'].append('ORDER_BOOK_NOT_OBSERVED')
        if ev['reaction_zones'] and ev['order_book'].get('status')=='OBSERVED':
            ev['status']='OBSERVED_EVIDENCE_RESEARCH'
        ev['blocking_reasons']+=['TRADE_BY_PRICE_VOLUME_NOT_AVAILABLE',
            'LONG_TERM_BOOK_PERSISTENCE_NOT_PROVEN','BACKTEST_NOT_COMPLETED','RESEARCH_ONLY']
        result['evidence_v161'][asset]=ev;item['evidence_v161']=ev;item['trade_authorized']=False
    result['totals']=dict(result.get('totals',{}),evidence_assets=len(result['evidence_v161']),
        observed_evidence_assets=sum(x['status']=='OBSERVED_EVIDENCE_RESEARCH' for x in result['evidence_v161'].values()),
        trade_authorized=0)
    result.update(signals=[],signals_enabled=False,trading_enabled=False,release_6_0_0_approved=False,
       continuous_freshness_proven=False,backtest_completed=False,research_only=True)
    return result
