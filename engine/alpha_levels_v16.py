"""v1.6 multi-timeframe pivot-zone research. Fail closed and never authorize trading."""
from copy import deepcopy
from decimal import Decimal as D, InvalidOperation
from engine.alpha_risk_v15 import get_closed_candles, validated_series, atr14

VERSION='alpha-1.6-multitimeframe-level-quality-research'
TF_CFG=(('4h','4H',14400,65),('1D','1Dutc',86400,100))

def num(v):
    try:
        x=D(str(v));return x if x.is_finite() else None
    except (ValueError, TypeError, InvalidOperation):return None

def f(x):return format(x.quantize(D('0.00000001')).normalize(),'f')

def pivots(rows, tf):
    out=[]
    for i in range(2,len(rows)-2):
        left=rows[i-2:i];right=rows[i+1:i+3]
        high=rows[i][2];low=rows[i][3]
        if high>max(r[2] for r in left+right):out.append({'timeframe':tf,'side':'resistance','price':high,'epoch':rows[i][0]})
        if low<min(r[3] for r in left+right):out.append({'timeframe':tf,'side':'support','price':low,'epoch':rows[i][0]})
    return out

def cluster(piv, tolerance):
    # Group price-nearby pivots; separate supports from resistances; deterministic.
    groups=[]
    for point in sorted(piv,key=lambda x:(x['side'],x['price'],x['timeframe'],x['epoch'])):
        candidates=[g for g in groups if g['side']==point['side'] and abs(point['price']-g['center'])<=tolerance]
        if candidates:
            g=min(candidates,key=lambda q:abs(q['center']-point['price']))
            g['points'].append(point)
            g['center']=sum(p['price'] for p in g['points'])/D(len(g['points']))
        else:groups.append({'side':point['side'],'center':point['price'],'points':[point]})
    return groups

def quality(g,last_ts):
    pts=g['points'];tfs={p['timeframe'] for p in pts}
    # No OHLCV volume from v15; do not claim volume-confirmed quality.
    tf_score=25 if '1D' in tfs else 16
    confirmations=min(20,5*len({(p['timeframe'],p['epoch']) for p in pts}))
    confluence=15 if len(tfs)>1 else 0
    latest=max(p['epoch'] for p in pts)
    age=max(0,last_ts-latest)
    freshness=10 if age<=7*86400 else (6 if age<=30*86400 else 2)
    total=tf_score+confirmations+confluence+freshness
    # out of 70 evidenced points. Unavailable price-reaction/volume score = 0 of 30.
    return {'partial_score_out_of_100':total,'evidence_cap':70,
            'scoring_components':{'timeframe_importance':tf_score,'pivot_observations':confirmations,
                                  'multi_timeframe_overlap':confluence,'recency':freshness,
                                  'post_touch_reaction_unmeasured':0,'volume_at_level_unmeasured':0},
            'evidence_quality':'PARTIAL_NO_VOLUME_OR_REACTION_VALIDATION'}

def inspect_asset(asset,market,get_candles=get_closed_candles):
    out={'status':'BLOCKED_UNVERIFIED_LEVEL_QUALITY','research_only':True,
         'zones':[],'nearest_overhead_zone':None,'dominant_overhead_zone':None,
         'nearest_support_zone':None,'data_validation':{},'blocking_reasons':[],
         'trade_authorized':False,'signals_authorized':False}
    tf=market.get('timeframes',{})
    try:
        if any(tf.get(k,{}).get('status')!='VALIDATED' for k in ('4h','1D')):
            raise ValueError('FOUR_HOUR_AND_DAILY_REPORT_NOT_VALIDATED')
        history={}
        for timeframe,bar,step,_ in TF_CFG:
            report=tf[timeframe]
            rows=validated_series(get_candles(asset,bar),report['identity'],step)
            if rows[-1][4]!=num(report['close']):raise ValueError('REPORT_CLOSE_MISMATCH_'+timeframe)
            history[timeframe]=rows
        entry=num(tf['4h']['close']);last_ts=history['4h'][-1][0]
        if entry is None or entry<=0:raise ValueError('INVALID_ENTRY_REFERENCE')
        a4=atr14(history['4h'])
        # Confluence zone tolerance is volatility-aware but capped at 1% of entry.
        tolerance=min(entry*D('0.01'),a4*D('0.25'))
        if tolerance<=0:raise ValueError('INVALID_ZONE_TOLERANCE')
        points=pivots(history['4h'],'4h')+pivots(history['1D'],'1D')
        if not points:raise ValueError('NO_CONFIRMED_PIVOTS')
        zones=[]
        for g in cluster(points,tolerance):
            qs=quality(g,last_ts)
            lo=min(p['price'] for p in g['points']);hi=max(p['price'] for p in g['points'])
            zone={'side':g['side'],'low':f(lo),'high':f(hi),'center':f(g['center']),
                  'timeframes':sorted({p['timeframe'] for p in g['points']}),
                  'independent_pivot_count':len({(p['timeframe'],p['epoch']) for p in g['points']}),
                  'confirmed_pivot_epochs':sorted({p['epoch'] for p in g['points']}),**qs}
            zones.append(zone)
        overhead=[z for z in zones if z['side']=='resistance' and num(z['low'])>entry]
        supports=[z for z in zones if z['side']=='support' and num(z['high'])<entry]
        near=min(overhead,key=lambda z:num(z['low'])) if overhead else None
        dominant=max(overhead,key=lambda z:(z['partial_score_out_of_100'],-num(z['low']))) if overhead else None
        supp=max(supports,key=lambda z:num(z['high'])) if supports else None
        out.update(status='PARTIAL_LEVEL_QUALITY_RESEARCH',zones=zones,
                   nearest_overhead_zone=near,dominant_overhead_zone=dominant,
                   nearest_support_zone=supp,
                   data_validation={'timeframes':['4h','1D'],'candle_identities_matched':True,
                       'closed_candles_4h':len(history['4h']),'closed_candles_daily':len(history['1D']),
                       'atr14_4h':f(a4),'zone_tolerance':f(tolerance)})
        if not overhead:out['blocking_reasons'].append('NO_CONFIRMED_OVERHEAD_PIVOT_ZONE')
        if not supports:out['blocking_reasons'].append('NO_CONFIRMED_SUPPORT_PIVOT_ZONE')
    except (ValueError, KeyError, TypeError, IndexError, OSError,TimeoutError) as e:
        out['blocking_reasons'].append(str(e)[:100])
    out['blocking_reasons']+=['LEVEL_VOLUME_PROFILE_NOT_VALIDATED',
          'INDEPENDENT_BOUNCE_STRENGTH_NOT_VALIDATED','ORDER_BOOK_HISTORY_UNAVAILABLE',
          'SPREAD_FEES_SLIPPAGE_UNVERIFIED','BACKTEST_NOT_COMPLETED','RESEARCH_ONLY']
    return out

def overlay(report,get_candles=get_closed_candles):
    if report.get('version')!='alpha-1.5.1-resistance-gates-research':
        raise ValueError('EXPECTED_V151_BASE_REPORT')
    out=deepcopy(report);out['version']=VERSION
    out['level_quality_v16']={}
    for asset,market in sorted(out.get('assets',{}).items()):
        z=inspect_asset(asset,market,get_candles)
        out['level_quality_v16'][asset]=z;market['level_quality_v16']=z
        market['trade_authorized']=False
    out['totals']=dict(out.get('totals',{}),level_quality_assets=len(out['level_quality_v16']),
           level_quality_partial=sum(v['status']=='PARTIAL_LEVEL_QUALITY_RESEARCH' for v in out['level_quality_v16'].values()),trade_authorized=0)
    out.update(signals=[],signals_enabled=False,trading_enabled=False,release_6_0_0_approved=False,
        continuous_freshness_proven=False,backtest_completed=False,research_only=True)
    return out
