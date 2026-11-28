"""Research-only causal feature separation; no calibrated probabilities."""
from decimal import Decimal as D
from statistics import median
from collections import Counter
from engine.alpha_body_levels_v168 import extract
from engine.alpha_importance_v179 import score_level
from engine.alpha_belts_v178 import observe_zone

def features(z,past,tolerance):
    level=D(z['body_level']); side=z['type']
    responses=[D(e['response_atr']) for e in z['events']]
    # Count distinct contiguous touch episodes, not individual candles.
    touches=[b[3]<=level+tolerance and b[2]>=level-tolerance for b in past]
    episodes=sum(t and (i==0 or not touches[i-1]) for i,t in enumerate(touches))
    change=past[-1][4]/past[-21][4]-1
    aligned=change if side=='support' else -change
    return {'structural_pivots':z['body_pivot_count'],
            'confirmed_rejections':z['confirmed_approach_rejections'],
            'median_response_atr':str(median(responses)) if responses else None,
            'touch_episodes':episodes,'aligned_return_20':str(aligned),
            'legacy_score':score_level('4h',z['body_pivot_count'],z['confirmed_approach_rejections'])}

def evaluate(bars):
    if len(bars)<126 or any(b[0]-a[0]!=14400 for a,b in zip(bars,bars[1:])):
        raise ValueError('INVALID_HISTORY')
    boundary=bars[len(bars)*7//10][0]
    events=[]
    for stop in range(90,len(bars)-12+1,12):
        past=bars[stop-90:stop]; future=bars[stop:stop+12]
        epoch=future[0][0]
        if epoch<boundary<epoch+12*14400:continue
        snap=extract('4h',past)
        for z in snap['candidates']:
            if z['type'] not in ('support','resistance'):continue
            level=D(z['body_level'])
            events.append({'decision_epoch':epoch,'partition':'earlier' if epoch<boundary else 'holdout',
                           'side':z['type'],'level':str(level),
                           **features(z,past,D(snap['tolerance'])),
                           'outcome':observe_zone(z['type'],level,level,future)})
    groups={}
    for partition in ('earlier','holdout'):
        rows=[e for e in events if e['partition']==partition]
        groups[partition]={}
        for feature in ('structural_pivots','confirmed_rejections','touch_episodes','legacy_score'):
            counts={}
            for e in rows:
                counts.setdefault(str(e[feature]),Counter())[e['outcome']]+=1
            groups[partition][feature]={k:dict(v) for k,v in counts.items()}
        for feature in ('median_response_atr','aligned_return_20'):
            counts={}
            for e in rows:
                v=e[feature]
                key='missing' if v is None else ('positive' if D(v)>0 else 'nonpositive')
                if feature=='median_response_atr' and v is not None:key='at_least_1_atr' if D(v)>=1 else 'below_1_atr'
                counts.setdefault(key,Counter())[e['outcome']]+=1
            groups[partition][feature]={k:dict(v) for k,v in counts.items()}
    return {'version':'alpha-2.1.1','events':events,'groups':groups,'research_only':True,
            'signals_enabled':False,'trading_enabled':False,'trade_authorized':False,'backtest_completed':False,
            'limitations':['TOUCH_COUNT_NOT_PROVEN_FATIGUE','TREND_PROXY_ONLY','REUSED_HISTORY','CORRELATED_LEVELS','NO_CALIBRATED_WEIGHTS']}
