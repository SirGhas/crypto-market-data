"""Strict resistance challenge/rejection audit based on actual closed OHLCV.
Research only. No order placement, trading or signals. Live candle data never used.
"""
from decimal import Decimal as D, InvalidOperation
from copy import deepcopy
import json, urllib.request, urllib.parse, time

VERSION='alpha-1.6.7-resistance-rejection-audit'

def dec(x):
    try:
        v=D(str(x));return v if v.is_finite() else None
    except (ValueError,TypeError,InvalidOperation):return None

def fmt(x):return format(x.quantize(D('.00000001')).normalize(),'f')

def closed_candles(asset,tf,now=None,transport=None):
    """Use 100 most recent confirmed contiguous bars from OKX spot, fail closed."""
    bar,period={'4h':('4H',14400),'1D':('1Dutc',86400)}[tf]
    args=urllib.parse.urlencode({'instId':asset+'-USDT','bar':bar,'limit':'100'})
    url='https://www.okx.com/api/v5/market/candles?'+args
    if transport:payload=transport(url)
    else:
        req=urllib.request.Request(url,headers={'User-Agent':'alpha-v167-resistance-audit/1.0'})
        with urllib.request.urlopen(req,timeout=18) as f:payload=json.load(f)
    if not isinstance(payload,dict) or payload.get('code')!='0' or not isinstance(payload.get('data'),list):
        raise ValueError('EXCHANGE_RESPONSE_INVALID')
    n=int(time.time()) if now is None else int(now)
    seen=set();bars=[]
    for row in payload['data']:
        if not isinstance(row,list) or len(row)<9 or str(row[8])!='1':continue
        t=int(row[0])//1000
        if t in seen:raise ValueError('DUPLICATE_CANDLE')
        seen.add(t)
        o,h,l,c,v=(dec(row[i]) for i in (1,2,3,4,5))
        if any(x is None for x in (o,h,l,c,v)) or min(o,h,l,c)<=0 or v<0 or h<max(o,c,l) or l>min(o,c,h):
            raise ValueError('INVALID_OHLCV')
        if t%period or t+period>n:raise ValueError('NON_CLOSED_OR_MISALIGNED_CANDLE')
        bars.append((t,o,h,l,c,v))
    bars.sort()
    if len(bars)<40 or any(b[0]-a[0]!=period for a,b in zip(bars,bars[1:])):
        raise ValueError('INSUFFICIENT_CONTIGUOUS_CANDLES')
    return bars

def evaluate_zone(zone,bars,atr,tf,tolerance_fraction=D('.10')):
    """Count separate approaches from below with directional rejection and two closed confirmation bars."""
    lo,hi=dec(zone.get('low')),dec(zone.get('high'))
    a=dec(atr)
    if None in (lo,hi,a) or not 0<lo<=hi or a<=0:raise ValueError('BAD_ZONE_OR_ATR')
    tol=a*tolerance_fraction
    events=[];last=-100
    for i in range(20,len(bars)-2):
        if i-last<6:continue
        prev=bars[i-1];b=bars[i]
        t,o,h,l,c,v=b
        approached=prev[4]<lo-tol and prev[2]<lo+tol and h>=lo-tol
        rejected=c<lo and c<o and h>c
        nexttwo=bars[i+1:i+3]
        confirms=max(k[4] for k in nexttwo)<hi+tol and min(k[3] for k in nexttwo)<=lo-D('.3')*a
        mean=sum(x[5] for x in bars[i-20:i])/D(20)
        rvol=v/mean if mean>0 else None
        if approached and rejected and confirms:
            excursion=(lo-min(k[3] for k in nexttwo))/a
            events.append({'start_epoch':t,'timeframe':tf,'approach_from_below':True,
                           'rejection_close':fmt(c),'rejection_candle_down':True,
                           'subsequent_low':fmt(min(k[3] for k in nexttwo)),
                           'reaction_atr':fmt(excursion),'candle_rvol20':fmt(rvol) if rvol is not None else None,
                           'volume_is_at_level':False})
            last=i
    return {'status':'CAUSAL_PRICE_REJECTION_AUDITED','event_count':len(events),'events':events,
            'only_closed_candles':True,'reaction_not_trade_by_price':True,
            'limits':['NO_BUY_SELL_TAKER_FLOW','NO_TRADE_BY_PRICE_VOLUME',
                      'ONLY_LAST_100_CLOSED_CANDLES','NO_LONG_TERM_BACKTEST']}

def zone_report(asset,item,histories):
    src=item.get('level_quality_v16',{});risk=item.get('risk_v15',{})
    atr=dec(risk.get('atr14_4h'))
    dailyatr=dec(risk.get('atr14_daily'))
    if atr is None or dailyatr is None:raise ValueError('UNVERIFIED_ATR')
    zones=[]
    for z in src.get('zones',[]):
        if z.get('side')!='resistance':continue
        record={'low':z['low'],'high':z['high'],
                'original_partial_score':z.get('partial_score_out_of_100'),
                'pivot_count':z.get('independent_pivot_count'),
                'timeframes':z.get('timeframes'),
                'closed_candle_rejection_audit':{}}
        for tf,a in [('4h',atr),('1D',dailyatr)]:
            try:record['closed_candle_rejection_audit'][tf]=evaluate_zone(z,histories[tf],a,tf)
            except Exception as e:record['closed_candle_rejection_audit'][tf]={'status':'NOT_VALIDATED','reason':str(e)[:100]}
        n4=record['closed_candle_rejection_audit']['4h'].get('event_count',0)
        nd=record['closed_candle_rejection_audit']['1D'].get('event_count',0)
        record['classification']=('REJECTION_OBSERVED_NEEDS_CROSS_TF_DEDUP' if n4 or nd else
                                   'PIVOT_ONLY_NO_VERIFIED_REJECTION_IN_OBSERVED_WINDOW')
        record['trade_authorized']=False
        zones.append(record)
    zones.sort(key=lambda x:D(x['low']))
    return {'status':'RESEARCH_ONLY','asset':asset,'resistance_zones':zones,
            'no_verified_seller_pressure':True,'trade_authorized':False}

def overlay(report,histories):
    if report.get('version')!='alpha-1.6.5-depth-sweep-research':raise ValueError('BASELINE_VERSION_MISMATCH')
    out=deepcopy(report);out['version']=VERSION;out['resistance_rejection_v167']={}
    for asset,item in out['assets'].items():
        try:
            expected={tf:item['timeframes'][tf]['identity'] for tf in ('4h','1D')}
            for tf in ('4h','1D'):
                candles=histories.get(asset,{}).get(tf,[])
                if not candles or str(candles[-1][0])+(':'+('240' if tf=='4h' else '1440'))!=expected[tf]:
                    raise ValueError('REPORT_CANDLE_IDENTITY_NOT_MATCHED')
                if dec(item['timeframes'][tf]['close'])!=candles[-1][4]:
                    raise ValueError('REPORT_CANDLE_CLOSE_NOT_MATCHED')
            value=zone_report(asset,item,histories[asset])
        except Exception as e:
            value={'status':'BLOCKED','asset':asset,'reason':str(e)[:120],
                   'resistance_zones':[],'trade_authorized':False}
        out['resistance_rejection_v167'][asset]=value
        item['resistance_rejection_v167']=value
    out['totals']=dict(out.get('totals',{}),resistance_audited_assets=sum(v['status']=='RESEARCH_ONLY' for v in out['resistance_rejection_v167'].values()),trade_authorized=0,signals=0)
    out.update(signals=[],signals_enabled=False,trading_enabled=False,trade_authorized=False,
               research_only=True,continuous_freshness_proven=False,backtest_completed=False)
    return out
