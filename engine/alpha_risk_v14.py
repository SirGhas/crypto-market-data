"""Research-only structure/risk overlay; no unsupported ATR or trade authorization."""
from copy import deepcopy
from decimal import Decimal as D, InvalidOperation
from hashlib import sha256
import json

VERSION='alpha-1.4-structural-risk-research'
TIMEFRAMES=('15m','30m','1h','2h','4h','1D')
TARGET_RS=(D('2'),D('2.5'),D('3'))

def dec(x):
    try:
        d=D(str(x))
        return d if d.is_finite() else None
    except (TypeError,InvalidOperation,ValueError):return None

def fmt(x):
    return format(x.quantize(D('0.000001')).normalize(),'f')

def compute_risk(asset, market):
    t=market.get('timeframes',{})
    primary=t.get('4h',{});daily=t.get('1D',{})
    out={'asset':asset,'status':'BLOCKED_UNVERIFIED_RISK', 'research_only':True,
         'reference_candle':primary.get('identity'),'daily_candle':daily.get('identity'),
         'candidate_entry_reference':None,'4h_support_levels':{},'daily_support_levels':{},
         '4h_overhead_resistance_levels':{},'daily_overhead_resistance_levels':{},
         'nearest_4h_support':None,'nearest_4h_overhead_resistance':None,
         'nearest_daily_overhead_resistance':None,'distance_to_4h_support_pct':None,
         'hypothetical_stop':None,'structural_stop_verified':False,
         'atr14_4h_verified':False,'atr14_daily_verified':False,
         'liquidity_spread_verified':False,'fees_slippage_verified':False,
         'targets_by_R':{str(r):None for r in TARGET_RS},
         'risk_reward_ratios':{str(r):None for r in TARGET_RS},
         'trade_authorized':False,'signals_authorized':False,
         'blocking_reasons':[]}
    if primary.get('status')!='VALIDATED' or daily.get('status')!='VALIDATED':
        out['blocking_reasons'].append('MISSING_VALID_CLOSED_4H_OR_DAILY')
        return out
    entry=dec(primary.get('close'))
    if entry is None or entry<=0:
        out['blocking_reasons'].append('INVALID_REFERENCE_CLOSE');return out
    out['candidate_entry_reference']=fmt(entry)
    support=[];upper4=[];upperD=[]
    for tf,name,acc in ((primary,'4h',upper4),(daily,'daily',upperD)):
        for window,item in tf.get('static_levels',{}).items():
            s=dec(item.get('support'));r=dec(item.get('resistance'))
            if s is not None and 0<s<entry:
                out[f'{name}_support_levels'][str(window)]=fmt(s)
                if name=='4h':support.append(s)
            if r is not None and r>entry:
                out[f'{name}_overhead_resistance_levels'][str(window)]=fmt(r)
                acc.append(r)
    if support:
        nearest=max(support)
        out['nearest_4h_support']=fmt(nearest)
        out['distance_to_4h_support_pct']=fmt((entry-nearest)/entry*100)
    else:out['blocking_reasons'].append('NO_VALID_4H_SUPPORT_BELOW_PRICE')
    if upper4:out['nearest_4h_overhead_resistance']=fmt(min(upper4))
    else:out['blocking_reasons'].append('NO_VERIFIED_OVERHEAD_4H_RESISTANCE')
    if upperD:out['nearest_daily_overhead_resistance']=fmt(min(upperD))
    else:out['blocking_reasons'].append('NO_VERIFIED_OVERHEAD_DAILY_RESISTANCE')
    # Previous data snapshots contain no ATR14 series, executable bid/ask spread,
    # fees/slippage validation or a confirmed causal pivot. The support above
    # is an observation, NOT a trade stop. Never infer such evidence from 1 candle.
    out['blocking_reasons'] += ['ATR14_4H_NOT_AVAILABLE','ATR14_DAILY_NOT_AVAILABLE',
                                 'STRUCTURAL_STOP_NOT_VALIDATED',
                                 'SPREAD_LIQUIDITY_NOT_VALIDATED','FEES_SLIPPAGE_NOT_VALIDATED',
                                 'RR_2_2_5_3_NOT_VALIDATED','RESEARCH_ONLY']
    return out

def merge_related_alerts(alerts):
    """Presentation grouping only; preserve each underlying event and its ID."""
    groups={}
    for event in alerts:
        if not isinstance(event,dict):continue
        asset=event.get('asset');kind=event.get('type');direction=event.get('direction')
        # Merge support breaks in different lower timeframes for same asset/run.
        if kind=='DOWNSIDE_SUPPORT_BREAK' and event.get('timeframe') in ('15m','30m'):
            key=(asset,kind,direction)
        else:key=(asset,kind,direction,event.get('event_id'))
        groups.setdefault(key,[]).append(event)
    bundles=[]
    for items in groups.values():
        identifiers=sorted({e.get('event_id') for e in items if e.get('event_id')})
        payload={'asset':items[0].get('asset'),'type':items[0].get('type'),
                 'direction':items[0].get('direction'),
                 'timeframes':sorted({e.get('timeframe') for e in items if e.get('timeframe')},
                                     key=lambda tf:TIMEFRAMES.index(tf) if tf in TIMEFRAMES else 99),
                 'underlying_event_ids':identifiers,
                 'underlying_event_count':len(items),
                 'research_only':True,'not_a_trade_instruction':True}
        payload['bundle_id']=sha256(json.dumps(identifiers,sort_keys=True).encode()).hexdigest()[:24]
        bundles.append(payload)
    return bundles

def overlay(document):
    if document.get('version')!='alpha-1.3-directional-research-alerts':
        raise ValueError('Expected validated Alpha 1.3 input')
    result=deepcopy(document)
    result['version']=VERSION
    result['risk_research']={name:compute_risk(name,market) for name,market in sorted(result.get('assets',{}).items())}
    result['alert_bundles']=merge_related_alerts(result.get('research_alerts',[]))
    result['risk_methodology']='Observed closed 4h/daily static levels only; ATR and executable trade risk pending validation.'
    result['signals']=[]
    result['research_only']=True;result['signals_enabled']=False;result['trading_enabled']=False
    result['release_6_0_0_approved']=False;result['backtest_completed']=False
    result['totals']=dict(result.get('totals',{}),risk_records=len(result['risk_research']),
                          alert_bundles=len(result['alert_bundles']))
    for item in result.get('assets',{}).values():item['trade_authorized']=False
    return result
