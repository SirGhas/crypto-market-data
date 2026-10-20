"""v1.8.2 BTC 4h causal, temporally separated structural-score audit.

An exploratory forward-only chronological split. Levels from the same decision
window are clustered for reporting; they are NOT independent samples.
No predictive calibration, signal generation, or execution backtest.
"""
import json
from collections import Counter
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_score_audit_v180 import evaluate as replay
from engine.alpha_score_audit_v181 import BINS

OUTCOMES=('NO_TOUCH','CONFIRMED_REJECTION','CONFIRMED_CLOSE_THROUGH',
          'TOUCH_AMBIGUOUS','TOUCH_UNRESOLVED')

def band(score):
    matches=[name for name,lo,hi in BINS if lo<=score<hi]
    if len(matches)!=1:raise ValueError('SCORE_OUTSIDE_BINS')
    return matches[0]

def aggregate(events):
    decisions=sorted({e['decision_epoch'] for e in events})
    counts={name:{'levels':0,'touched':0,'confirmed_rejections':0,
                  'confirmed_breakouts':0,'ambiguous':0,'unresolved':0,
                  'distinct_decisions':0} for name,_,_ in BINS}
    for e in events:
        if e['outcome'] not in OUTCOMES:raise ValueError('INVALID_OUTCOME')
        s=counts[band(e['heuristic_score'])]
        s['levels']+=1
        if e['outcome']!='NO_TOUCH':s['touched']+=1
        if e['outcome']=='CONFIRMED_REJECTION':s['confirmed_rejections']+=1
        if e['outcome']=='CONFIRMED_CLOSE_THROUGH':s['confirmed_breakouts']+=1
        if e['outcome']=='TOUCH_AMBIGUOUS':s['ambiguous']+=1
        if e['outcome']=='TOUCH_UNRESOLVED':s['unresolved']+=1
    for name in counts:
        counts[name]['distinct_decisions']=len({e['decision_epoch'] for e in events
                                                 if band(e['heuristic_score'])==name})
    return {'decision_windows':len(decisions),'levels':len(events),
            'by_band':counts}

def evaluate(bars,lookback=90,horizon=12,stride=12,train_fraction=0.6):
    if not 0.25<=train_fraction<=0.75:raise ValueError('INVALID_TRAIN_FRACTION')
    original=replay(bars,lookback=lookback,horizon=horizon,stride=stride)
    events=original['events']
    decisions=sorted({e['decision_epoch'] for e in events})
    if len(decisions)<4:raise ValueError('INSUFFICIENT_DECISION_WINDOWS')
    # Fixed, chronological partition. No threshold fitting on test outcomes.
    cut=max(1,min(len(decisions)-1,int(len(decisions)*train_fraction)))
    first_test=decisions[cut]
    train=[e for e in events if e['decision_epoch']<first_test]
    test=[e for e in events if e['decision_epoch']>=first_test]
    if not train or not test:raise ValueError('EMPTY_TIME_SPLIT')
    # Future evaluation horizons must not overlap between partitions.
    last_train=max(e['decision_epoch'] for e in train)
    if last_train+(horizon-1)*14400>=first_test:
        train=[e for e in train if e['decision_epoch']+(horizon-1)*14400<first_test]
        if not train:raise ValueError('NO_PURGED_TRAIN_WINDOWS')
    return {'version':'alpha-1.8.2-btc-4h-chronological-audit',
        'asset':'BTC','timeframe':'4h','historical_closed_bars':len(bars),
        'lookback_bars':lookback,'horizon_bars':horizon,'stride_bars':stride,
        'train_fraction':train_fraction,'first_test_decision_epoch':first_test,
        'train':aggregate(train),'held_out':aggregate(test),
        'metric_interpretation':'DESCRIPTIVE_COUNTS_NOT_PROBABILITIES',
        'sampling_unit':'DECISION_WINDOW_LEVELS_CLUSTERED_NOT_INDEPENDENT',
        'thresholds_frozen_before_held_out_observations':True,
        'limitations':['SINGLE_HISTORICAL_SLICE','SAME_MARKET_EPISODES_ACROSS_WINDOWS',
                       'NO_INDEPENDENT_EVENTS_OR_CONFIDENCE_INTERVALS',
                       'NO_PROVEN_OUT_OF_SAMPLE_GENERALIZATION',
                       'ONLY_4H_BTC','NO_EXECUTION_BACKTEST',
                       'SCORE_BINS_UNCALIBRATED','NO_TRADING_OR_SIGNALS'],
        'research_only':True,'signals':[],'signals_enabled':False,
        'trading_enabled':False,'trade_authorized':False,
        'backtest_completed':False,'continuous_freshness_proven':False,
        'release_6_0_0_approved':False}

def main():
    report=evaluate(history_4h(pages=12))
    dest=Path('artifacts/alpha_swing_v182_btc_chronological_audit.json')
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('ALPHA_V182',json.dumps({'train':report['train'],
         'held_out':report['held_out'],'trades':0,'signals':0}))

if __name__=='__main__':main()
