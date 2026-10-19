"""Alpha 1.5.1: resistance-first, fail-closed spot research decision overlay.

Never treats a projected breakout as achieved, nor a hypothetical stop as executable.
"""
from copy import deepcopy
from decimal import Decimal as D, InvalidOperation

VERSION='alpha-1.5.1-resistance-gates-research'
RS=('2','2.5','3')

def dec(v):
    try:
        x=D(str(v))
        return x if x.is_finite() else None
    except (ValueError,TypeError,InvalidOperation):return None

def fmt(x):
    return format(x.quantize(D('0.00000001')).normalize(),'f')

def resistance_gate(name,market,legacy):
    risk=market.get('risk_v15',{})
    tf=market.get('timeframes',{})
    four=tf.get('4h',{}); day=tf.get('1D',{})
    old=legacy or market.get('risk_research',{})
    entry=dec(four.get('close')); stop=dec(risk.get('hypothetical_stop'))
    result={'asset':name,'status':'BLOCKED_UNVERIFIED_RISK','research_only':True,
        'entry_reference':fmt(entry) if entry is not None else None,
        'first_four_hour_resistance':None,'first_daily_resistance':None,
        'nearest_overhead_resistance':None,'distance_to_nearest_resistance_pct':None,
        'gross_risk_per_unit':None,'gross_reward_to_first_resistance':None,
        'gross_rr_to_first_resistance':None,
        'gross_targets_by_R':{r:None for r in RS},
        'targets_clear_first_resistance':{r:None for r in RS},
        'breakout_watch':False,'breakout_validated':False,
        'breakout_retest_validated':False,'daily_breakout_validated':False,
        'net_rr_after_costs':None,'blocking_reasons':[],
        'trade_authorized':False,'signals_authorized':False}
    problems=result['blocking_reasons']
    if four.get('status')!='VALIDATED' or day.get('status')!='VALIDATED':problems.append('MISSING_VALID_CLOSED_4H_OR_DAILY')
    if entry is None or entry<=0:problems.append('INVALID_4H_ENTRY_REFERENCE')
    if risk.get('data_validation',{}).get('matched_report_candle_identities') is not True:
        problems.append('UNVERIFIED_SYNCHRONIZED_ATR_SERIES')
    if stop is None or entry is None or not D(0)<stop<entry:
        problems.append('NO_VALID_HYPOTHETICAL_STRUCTURAL_STOP')
    else:
        unit=entry-stop;result['gross_risk_per_unit']=fmt(unit)
        result['gross_targets_by_R']={r:fmt(entry+D(r)*unit) for r in RS}
    if entry is not None and entry>0:
        pools=[]
        for label,key in (('first_four_hour_resistance','4h_overhead_resistance_levels'),
                          ('first_daily_resistance','daily_overhead_resistance_levels')):
            values=old.get(key,{})
            if not isinstance(values,dict):values={}
            # Distinct causal historical resistance observations, no extrapolation.
            available=sorted({n for v in values.values() if (n:=dec(v)) is not None and n>entry})
            if available:
                result[label]=fmt(available[0]);pools.append(available[0])
            else:problems.append('NO_'+('FOUR_HOUR' if label.startswith('first_four') else 'DAILY')+'_OVERHEAD_RESISTANCE')
        if pools:
            first=min(pools)
            result['nearest_overhead_resistance']=fmt(first)
            result['distance_to_nearest_resistance_pct']=fmt((first-entry)/entry*100)
            result['gross_reward_to_first_resistance']=fmt(first-entry)
            if stop is not None and 0<stop<entry:
                rr=(first-entry)/(entry-stop)
                result['gross_rr_to_first_resistance']=fmt(rr)
                result['targets_clear_first_resistance']={r:entry+D(r)*(entry-stop)<=first for r in RS}
                if rr<D('2'):
                    problems.append('FIRST_RESISTANCE_BLOCKS_MINIMUM_2R')
            else:problems.append('REWARD_RISK_UNCOMPUTABLE')
    # Do not equate prior "broke_resistance" flag with a validated retest.
    rv=dec(four.get('rvol20'))
    positive=(four.get('candle_direction')=='UP' and rv is not None and rv>=D(1)
              and four.get('broke_resistance_20') is True)
    daily_confirmed=(day.get('status')=='VALIDATED' and
                     day.get('sma_close',{}).get('SMA233',{}).get('close_above') is True and
                     day.get('sma_close',{}).get('SMA233',{}).get('slope')=='UP')
    result['breakout_watch']=bool(positive)
    # Historical level crossing, subsequent retest, and daily resistance breakout require
    # their own time-aligned validation. None can be inferred from current report fields.
    if positive:problems.append('BREAKOUT_RETEST_AND_HISTORICAL_LEVEL_NOT_VALIDATED')
    if not daily_confirmed:problems.append('DAILY_TREND_NOT_CONFIRMED')
    problems += ['LIVE_SPREAD_UNVERIFIED','FEES_SLIPPAGE_UNVERIFIED',
                 'WALK_FORWARD_BACKTEST_NOT_COMPLETED','RESEARCH_ONLY']
    return result

def overlay(report):
    if report.get('version')!='alpha-1.5-causal-risk-research':
        raise ValueError('Expected Alpha 1.5 research report')
    result=deepcopy(report);result['version']=VERSION
    result['resistance_gates']={name:resistance_gate(name,market,report.get('risk_research',{}).get(name))
                                for name,market in sorted(result.get('assets',{}).items())}
    for name,v in result['resistance_gates'].items():
        result['assets'][name]['resistance_gate_v151']=v
        result['assets'][name]['trade_authorized']=False
    result['totals']=dict(result.get('totals',{}),resistance_gates=len(result['resistance_gates']),trade_authorized=0)
    result.update(signals=[],signals_enabled=False,trading_enabled=False,release_6_0_0_approved=False,
                  continuous_freshness_proven=False,backtest_completed=False,research_only=True)
    return result
