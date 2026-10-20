"""v1.7.8 strict 4h belt boundary observer and paired replay.
Research only. Wick touch is never an independently confirmed rejection.
"""
import json
from pathlib import Path
from decimal import Decimal as D
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_body_levels_v168 import extract,number
from engine.alpha_belts_v175 import build_belts
from engine.alpha_belts_v176 import PCT_CAPS

def observe_zone(side,lower,upper,future,confirmation=2):
    lo=D(str(lower));hi=D(str(upper))
    if lo>hi or confirmation<1:raise ValueError('INVALID_ZONE')
    for i,b in enumerate(future):
        high,low,close=b[2],b[3],b[4]
        touched=high>=lo if side=='resistance' else low<=hi
        if not touched:continue
        # First touch only. A bar spanning both boundaries cannot establish
        # chronological response; use later FULLY closed candles for confirmation.
        if i+confirmation>=len(future):return 'TOUCH_UNRESOLVED'
        following=future[i+1:i+1+confirmation]
        if side=='resistance':
            breakout=all(x[4]>hi for x in following)
            rejection=all(x[4]<lo for x in following)
        elif side=='support':
            breakout=all(x[4]<lo for x in following)
            rejection=all(x[4]>hi for x in following)
        else:raise ValueError('INVALID_SIDE')
        if breakout:return 'CONFIRMED_CLOSE_THROUGH'
        if rejection:return 'CONFIRMED_REJECTION'
        return 'TOUCH_AMBIGUOUS'
    return 'NO_TOUCH'

def audit(bars,lookback=90,horizon=12,stride=12):
    if len(bars)<lookback+horizon+stride*2:raise ValueError('INSUFFICIENT_HISTORY')
    if any(b[0]-a[0]!=14400 for a,b in zip(bars,bars[1:])):
        raise ValueError('NONCONTIGUOUS_HISTORY')
    events=[]
    for stop in range(lookback,len(bars)-horizon+1,stride):
        past=bars[stop-lookback:stop];future=bars[stop:stop+horizon]
        snap=extract('4h',past)
        price=number(snap['last_close']);atr=number(snap['atr14_simple_research'])
        levels=[{'side':z['type'],'price':number(z['body_level']),'timeframe':'4h'}
                for z in snap['candidates'] if z['type'] in ('support','resistance')]
        row={'decision_epoch':future[0][0],'past_last_epoch':past[-1][0],'variants':{}}
        for cap in PCT_CAPS:
            output=build_belts(levels,price,atr,pct_cap=cap)
            pairs=[]
            for zone in output['belts']:
                side=zone['side']
                belt=observe_zone(side,zone['lower_bound'],zone['upper_bound'],future)
                components=[observe_zone(side,m['price'],m['price'],future)
                            for m in zone['level_sources']]
                pairs.append({'side':side,'lower':zone['lower_bound'],'upper':zone['upper_bound'],
                    'belt_outcome':belt,'component_outcomes':components,
                    'any_component_rejection':'CONFIRMED_REJECTION' in components,
                    'any_component_breakout':'CONFIRMED_CLOSE_THROUGH' in components})
            row['variants'][str(cap)]=pairs
        events.append(row)
    result={}
    for cap in PCT_CAPS:
        key=str(cap);pairs=[p for row in events for p in row['variants'][key]]
        result[key]={'paired_occurrences':len(pairs),
            'belt_confirmed_rejection':sum(p['belt_outcome']=='CONFIRMED_REJECTION' for p in pairs),
            'component_any_rejection':sum(p['any_component_rejection'] for p in pairs),
            'belt_only_rejection':sum(p['belt_outcome']=='CONFIRMED_REJECTION' and not p['any_component_rejection'] for p in pairs),
            'component_only_rejection':sum(p['belt_outcome']!='CONFIRMED_REJECTION' and p['any_component_rejection'] for p in pairs),
            'belt_confirmed_breakout':sum(p['belt_outcome']=='CONFIRMED_CLOSE_THROUGH' for p in pairs),
            'belt_ambiguous':sum(p['belt_outcome']=='TOUCH_AMBIGUOUS' for p in pairs),
            'belt_unresolved':sum(p['belt_outcome']=='TOUCH_UNRESOLVED' for p in pairs),
            'belt_no_touch':sum(p['belt_outcome']=='NO_TOUCH' for p in pairs)}
    return {'version':'alpha-1.7.8-btc-strict-belt-boundary-audit',
        'asset':'BTC','timeframe':'4h','historical_closed_bars':len(bars),
        'evaluations':len(events),'lookback_bars':lookback,'horizon_bars':horizon,
        'results':result,'observations':events,
        'limitations':['4H_ONLY_NOT_MTF','TWO_NEXT_BAR_CLOSES_HEURISTIC',
            'NO_INTRABAR_SEQUENCE','NO_OOS_CALIBRATION','SPARSE_BELT_EVENTS',
            'DESCRIPTIVE_NOT_EXECUTION_BACKTEST','SAME_EVENTS_ACROSS_CAPS'],
        'research_only':True,'signals':[],'signals_enabled':False,'trading_enabled':False,
        'trade_authorized':False,'backtest_completed':False,'continuous_freshness_proven':False,
        'release_6_0_0_approved':False}

def main():
    report=audit(history_4h(pages=12))
    path=Path('artifacts/alpha_swing_v178_btc_boundary.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('ALPHA_V178',json.dumps({'results':report['results'],'trades':0,'signals':0}))
if __name__=='__main__':main()
