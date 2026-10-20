"""v1.7.6 BTC 4h historical belt-width sensitivity, research only.

Candidates and belt parameters from closed PAST bars only; FUTURE bars
are read exclusively for observations. Not an execution backtest.
"""
import json
from decimal import Decimal as D
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_body_levels_v168 import extract,number
from engine.alpha_belts_v175 import build_belts

PCT_CAPS=(D('.0005'),D('.001'),D('.002'),D('.003'))
HORIZON=12

def outcome(side,low,high,future):
    """Classify first touch conservatively; intrabar ambiguous stays unknown."""
    for i,b in enumerate(future):
        _,op,h,l,cl,_=b
        if side=='resistance':
            touch=h>=low
            if not touch:continue
            if cl>high:return 'CLOSE_THROUGH'
            if i+2>=len(future):return 'UNRESOLVED'
            subsequent=future[i+1:i+3]
            if any(z[4]>high for z in subsequent):return 'CLOSE_THROUGH'
            if any(z[4]<low for z in subsequent):return 'REJECTION_CLOSE'
            return 'TOUCH_UNRESOLVED'
        else:
            touch=l<=high
            if not touch:continue
            if cl<low:return 'CLOSE_THROUGH'
            if i+2>=len(future):return 'UNRESOLVED'
            subsequent=future[i+1:i+3]
            if any(z[4]<low for z in subsequent):return 'CLOSE_THROUGH'
            if any(z[4]>high for z in subsequent):return 'REJECTION_CLOSE'
            return 'TOUCH_UNRESOLVED'
    return 'NO_TOUCH'

def evaluate(bars,lookback=90,horizon=HORIZON,stride=12):
    if len(bars)<lookback+horizon+stride*2:raise ValueError('INSUFFICIENT_HISTORY')
    if any(y[0]-x[0]!=14400 for x,y in zip(bars,bars[1:])):
        raise ValueError('NONCONTIGUOUS_HISTORY')
    records=[]
    for stop in range(lookback,len(bars)-horizon+1,stride):
        past=bars[stop-lookback:stop];future=bars[stop:stop+horizon]
        snap=extract('4h',past)
        price=number(snap['last_close']);atr=number(snap['atr14_simple_research'])
        levels=[{'side':z['type'],'price':number(z['body_level']),'timeframe':'4h'}
                for z in snap['candidates'] if z['type'] in ('support','resistance')]
        record={'decision_epoch':future[0][0],'last_historical_epoch':past[-1][0],
                'variants':{}}
        for pct in PCT_CAPS:
            result=build_belts(levels,price,atr,pct_cap=pct)
            belt_obs=[outcome(z['side'],D(z['lower_bound']),D(z['upper_bound']),future)
                       for z in result['belts']]
            singles_obs=[outcome(z['side'],D(z['price']),D(z['price']),future)
                         for z in result['unmerged_levels']]
            record['variants'][str(pct)]={
                'belt_count':len(belt_obs),
                'single_count':len(singles_obs),
                'belt_outcomes':belt_obs,
                'single_outcomes':singles_obs}
        records.append(record)
    summary={}
    for pct in PCT_CAPS:
        key=str(pct);rows=[r['variants'][key] for r in records]
        belts=[o for r in rows for o in r['belt_outcomes']]
        singles=[o for r in rows for o in r['single_outcomes']]
        def count(arr):
            return {s:arr.count(s) for s in ('NO_TOUCH','REJECTION_CLOSE','CLOSE_THROUGH',
                                               'UNRESOLVED','TOUCH_UNRESOLVED')}
        summary[key]={'decisions':len(records),'belts':len(belts),
                      'singles':len(singles),'belt_outcomes':count(belts),
                      'single_outcomes':count(singles)}
    return {'version':'alpha-1.7.6-btc-4h-belt-historical-sensitivity',
        'asset':'BTC','timeframe':'4h','lookback_bars':lookback,'horizon_bars':horizon,
        'stride_bars':stride,'historical_closed_bars':len(bars),
        'experimental_pct_caps':[str(v) for v in PCT_CAPS],
        'results':summary,'observations':records,
        'important_scope':'4H_ONLY; NOT MULTI_TIMEFRAME HISTORICAL VALIDATION',
        'limitations':['PARAMETERS_NOT_OPTIMIZED','NO_TRAIN_TEST_SPLIT',
            'OVERLAPPING_LEVELS_NOT_INDEPENDENT','NO_CAUSAL_INTRABAR_SEQUENCE',
            'REJECTION_PROXY_UNCALIBRATED','BELTS_AND_LINES_DIFFERENT_SELECTION',
            'NOT_AN_EXECUTION_BACKTEST','NO_ORDERFLOW_PROOF'],
        'research_only':True,'signals':[],'signals_enabled':False,
        'trading_enabled':False,'trade_authorized':False,
        'backtest_completed':False,'continuous_freshness_proven':False,
        'release_6_0_0_approved':False}

def main():
    bars=history_4h(pages=12)
    data=evaluate(bars)
    path=Path('artifacts/alpha_swing_v176_btc_belt_sensitivity.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print('ALPHA_V176',json.dumps({'bars':len(bars),'summary':data['results'],
      'signals':0,'trades':0}))
if __name__=='__main__':main()
