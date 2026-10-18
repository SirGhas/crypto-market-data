"""Research-only causal multi-R OHLC simulation. Never generates trading signals."""
from decimal import Decimal as D
from engine.alpha_core import BARS
from engine.alpha_backtest_v09 import assess_exit, FEE, SLIP
WINDOWS=(20,60,120,233)
TARGETS=(D('2'),D('2.5'),D('3'))
HORIZON=12

def pivot_lows(cs, event, left=3, right=3):
    # a pivot at p is only known after p+right bars have CLOSED, never future bars
    return [(p,cs[p]['low']) for p in range(left,event-right+1)
            if all(cs[p]['low']<cs[j]['low'] for j in range(p-left,p))
            and all(cs[p]['low']<=cs[j]['low'] for j in range(p+1,p+right+1))]

def atr14(cs,i):
    ranges=[]
    for k in range(i-13,i+1):
        c=cs[k];prev=cs[k-1]['close']
        ranges.append(max(c['high']-c['low'],abs(c['high']-prev),abs(c['low']-prev)))
    return sum(ranges,D(0))/14

def scenario_result(cs,signal_index,entry,stop,rr,horizon=HORIZON):
    risk=entry-stop
    target=entry+rr*risk
    raw_exit,reason,held=assess_exit('LONG',entry,stop,target,cs[signal_index+1:signal_index+1+horizon])
    exit_price=raw_exit*(1-SLIP)
    net_r=((exit_price-entry)-(entry+exit_price)*FEE)/risk
    return {'target_rr':str(rr),'target':str(target),'exit_reason':reason,'holding_candles':held,
            'net_r_after_costs':str(net_r),'net_profitable':net_r>0,'signal_authorized':False}

def simulate(rows,tf,now,closed_count=399):
    period=BARS[tf][0];last=(now//period-1)*period
    stamps=[last-j*period for j in range(closed_count)][::-1]
    if any(t not in rows for t in stamps):
        return {'status':'BLOCKED','reason':'MISSING_CONTIGUOUS_CLOSED_HISTORY','events':[]}
    cs=[rows[t] for t in stamps]
    if any(any(k not in c for k in ('open','high','low','close','base_volume')) or
           not all(isinstance(c[k],D) and c[k].is_finite() for k in ('open','high','low','close','base_volume')) or
           c['low']<=0 or c['high']<max(c['open'],c['close'],c['low']) or
           c['low']>min(c['open'],c['close']) or c['base_volume']<0 for c in cs):
        return {'status':'BLOCKED','reason':'INVALID_OHLCV','events':[]}
    events=[];i=234;limit=len(cs)-HORIZON-1
    while i<=limit:
        current=cs[i]
        prior=cs[i-20:i]
        mean_volume=sum((c['base_volume'] for c in prior),D(0))/20
        if mean_volume<=0:i+=1;continue
        rvol=current['base_volume']/mean_volume
        sma=sum((c['close'] for c in cs[i-232:i+1]),D(0))/233
        prior_sma=sum((c['close'] for c in cs[i-233:i]),D(0))/233
        levels={str(w):{'support':str(min(c['low'] for c in cs[i-w:i])),
                         'resistance':str(max(c['high'] for c in cs[i-w:i]))} for w in WINDOWS}
        # Fixed entry rule across every RR scenario: short-term 20-bar breakout, volume, SMA233
        if not (current['close']>D(levels['20']['resistance']) and rvol>=D('1.5') and current['close']>sma and sma>prior_sma):
            i+=1;continue
        pivot_candidates=[(p,v) for p,v in pivot_lows(cs,i) if p>=i-120]
        atr=atr14(cs,i)
        if not pivot_candidates or atr<=0:i+=1;continue
        # Nearest previously confirmed lower swing: deterministic and causal.
        entry=cs[i+1]['open']*(1+SLIP)
        lower=[(p,v) for p,v in pivot_candidates if v<entry]
        if not lower:i+=1;continue
        chosen=max(v for _,v in lower)
        stop=chosen-D('0.2')*atr
        risk=entry-stop
        if risk<=0 or stop<=0:i+=1;continue
        overhead=[D(levels[str(w)]['resistance']) for w in (60,120,233)
                  if D(levels[str(w)]['resistance'])>entry]
        nearest=min(overhead) if overhead else None
        scenarios={str(rr):scenario_result(cs,i,entry,stop,rr) for rr in TARGETS}
        for rr in TARGETS:
            target=entry+rr*risk
            scenarios[str(rr)]['clear_to_next_static_resistance']= nearest is None or nearest>=target
        # strict: do not silently consider a filled target valid if a higher static resistance precedes it
        events.append({'event_id':f'{stamps[i]}:{period//60}','entry_id':f'{stamps[i+1]}:{period//60}',
                       'entry':str(entry),'stop':str(stop),'risk':str(risk),'atr14':str(atr),
                       'pivot_low':str(chosen),'sma233':str(sma),'rvol20':str(rvol),
                       'lookback_levels':levels,'nearest_overhead_resistance':str(nearest) if nearest else None,
                       'scenarios':scenarios,'research_only':True,'signal_authorized':False})
        # identical event sampling for all targets; no overlapping forward windows
        i+=HORIZON+1
    statistics={}
    for rr in TARGETS:
        s=str(rr); values=[D(e['scenarios'][s]['net_r_after_costs']) for e in events]
        eligible=[e for e in events if e['scenarios'][s]['clear_to_next_static_resistance']]
        ev=[D(e['scenarios'][s]['net_r_after_costs']) for e in eligible]
        statistics[s]={'sample_events':len(values),'mean_net_r_all':str(sum(values,D(0))/len(values)) if values else None,
                       'net_profitable_all':sum(v>0 for v in values),'static_resistance_clear_events':len(eligible),
                       'mean_net_r_static_clear':str(sum(ev,D(0))/len(ev)) if ev else None,
                       'net_profitable_static_clear':sum(v>0 for v in ev)}
    return {'status':'INSAMPLE_RESEARCH_SIMULATION','history_candles':len(cs),'candidate_events':len(events),
            'lookbacks':list(WINDOWS),'target_rrs':[str(x) for x in TARGETS],
            'entry_rule':'CLOSE_BREAK_20_RVOL_1_5_SMA233_UP','stop_rule':'CONFIRMED_SWING_LOW_120_MINUS_0_2_ATR14',
            'exit_policy':'NEXT_OPEN_ENTRY_STOP_FIRST_TIE_MAX_12_BARS',
            'execution_friction':{'fee_per_side':str(FEE),'slippage_per_side':str(SLIP)},
            'statistics':statistics,'events':events,'in_sample_only':True,'out_of_sample':False,
            'market_liquidity_validated':False,'signal_authorized':False}
