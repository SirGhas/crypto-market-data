"""v1.7.7 research-only paired belt vs own component levels, BTC closed 4h.
Descriptive paired replay, not a trading or out-of-sample performance test.
"""
import json
from pathlib import Path
from decimal import Decimal as D
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_body_levels_v168 import extract,number
from engine.alpha_belts_v175 import build_belts
from engine.alpha_belts_v176 import outcome,PCT_CAPS

def paired_audit(bars,lookback=90,horizon=12,stride=12):
    if len(bars)<lookback+horizon+2*stride:
        raise ValueError('INSUFFICIENT_HISTORY')
    if any(y[0]-x[0]!=14400 for x,y in zip(bars,bars[1:])):
        raise ValueError('NONCONTIGUOUS_HISTORY')
    rows=[]
    for stop in range(lookback,len(bars)-horizon+1,stride):
        past=bars[stop-lookback:stop];future=bars[stop:stop+horizon]
        snap=extract('4h',past)
        atr=number(snap['atr14_simple_research']);price=number(snap['last_close'])
        levels=[{'side':z['type'],'price':number(z['body_level']),'timeframe':'4h'}
            for z in snap['candidates'] if z['type'] in ('support','resistance')]
        rec={'decision_epoch':future[0][0],'past_last_epoch':past[-1][0],'variants':{}}
        for pct in PCT_CAPS:
            result=build_belts(levels,price,atr,pct_cap=pct)
            pairs=[]
            for belt in result['belts']:
                low=D(belt['lower_bound']);high=D(belt['upper_bound'])
                side=belt['side']
                members=[outcome(side,D(z['price']),D(z['price']),future) for z in belt['level_sources']]
                combined=outcome(side,low,high,future)
                # Multiple component levels can share identical reactions; don't
                # pretend each member is an independent market event.
                pairs.append({'lower':belt['lower_bound'],'upper':belt['upper_bound'],
                    'width_pct':belt['width_pct'],'side':side,'tier':belt['structural_tier'],
                    'member_count':len(members),'belt_outcome':combined,
                    'component_outcomes':members,
                    'any_component_rejection':('REJECTION_CLOSE' in members),
                    'any_component_breakthrough':('CLOSE_THROUGH' in members)})
            rec['variants'][str(pct)]=pairs
        rows.append(rec)
    summaries={}
    for pct in PCT_CAPS:
        key=str(pct)
        pairs=[p for row in rows for p in row['variants'][key]]
        summaries[key]={'paired_belt_occurrences':len(pairs),
            'belt_rejections':sum(p['belt_outcome']=='REJECTION_CLOSE' for p in pairs),
            'component_any_rejection':sum(p['any_component_rejection'] for p in pairs),
            'both_rejection':sum(p['belt_outcome']=='REJECTION_CLOSE' and p['any_component_rejection'] for p in pairs),
            'belt_only_rejection':sum(p['belt_outcome']=='REJECTION_CLOSE' and not p['any_component_rejection'] for p in pairs),
            'component_only_rejection':sum(p['belt_outcome']!='REJECTION_CLOSE' and p['any_component_rejection'] for p in pairs),
            'belt_no_touch':sum(p['belt_outcome']=='NO_TOUCH' for p in pairs),
            'belt_close_through':sum(p['belt_outcome']=='CLOSE_THROUGH' for p in pairs)}
    return {'version':'alpha-1.7.7-btc-paired-belt-component-audit',
        'asset':'BTC','timeframe':'4h','closed_bars':len(bars),
        'lookback':lookback,'horizon':horizon,'stride':stride,
        'summaries':summaries,'observations':rows,
        'interpretation':'DESCRIPTIVE_PAIRED_COMPARISON_ONLY',
        'limitations':['NOT_MULTITIMEFRAME','NO_TRAIN_VALIDATION_TEST_SPLIT',
          'FEW_BELT_OCCURRENCES','OUTCOME_HEURISTIC_NOT_CALIBRATED',
          'NO_INDEPENDENT_COMPONENT_EVENTS','NO_CAUSAL_INTRABAR_PATH',
          'PAIRED_REPLAY_NOT_EXECUTION_BACKTEST'],
        'research_only':True,'signals':[],'signals_enabled':False,
        'trading_enabled':False,'trade_authorized':False,
        'backtest_completed':False,'continuous_freshness_proven':False,
        'release_6_0_0_approved':False}

def main():
    result=paired_audit(history_4h(pages=12))
    path=Path('artifacts/alpha_swing_v177_btc_paired.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('ALPHA_V177',json.dumps({'summaries':result['summaries'],'signals':0,'trades':0}))
if __name__=='__main__':main()
