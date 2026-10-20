"""v1.8.0 BTC 4h causal structural-score stratification, research only.
Descriptive evaluation of prior-candle level evidence, not predictive validation.
"""
import json
from pathlib import Path
from decimal import Decimal as D
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_body_levels_v168 import extract,number
from engine.alpha_importance_v179 import score_level
from engine.alpha_belts_v178 import observe_zone

def evaluate(bars,lookback=90,horizon=12,stride=12):
    if len(bars)<lookback+horizon+2*stride:raise ValueError('INSUFFICIENT_HISTORY')
    if any(b[0]-a[0]!=14400 for a,b in zip(bars,bars[1:])):
        raise ValueError('NONCONTIGUOUS_HISTORY')
    events=[]
    for stop in range(lookback,len(bars)-horizon+1,stride):
        past=bars[stop-lookback:stop];future=bars[stop:stop+horizon]
        snap=extract('4h',past)
        for z in snap['candidates']:
            if z['type'] not in ('support','resistance'):continue
            level=number(z.get('body_level'))
            if level is None:continue
            score=score_level('4h',z.get('body_pivot_count') or 0,
                              z.get('confirmed_approach_rejections') or 0)
            label='HIGH' if score>=60 else ('MEDIUM' if score>=48 else 'LOW')
            events.append({'decision_epoch':future[0][0],
                'historical_last_epoch':past[-1][0],
                'level':str(level),'side':z['type'],
                'heuristic_score':score,'score_band':label,
                'outcome':observe_zone(z['type'],level,level,future)})
    metrics={}
    for group in ('LOW','MEDIUM','HIGH'):
        rows=[r for r in events if r['score_band']==group]
        touched=[r for r in rows if r['outcome']!='NO_TOUCH']
        metrics[group]={'observations':len(rows),'touched':len(touched),
            'confirmed_rejections':sum(r['outcome']=='CONFIRMED_REJECTION' for r in touched),
            'confirmed_breakouts':sum(r['outcome']=='CONFIRMED_CLOSE_THROUGH' for r in touched),
            'ambiguous':sum(r['outcome']=='TOUCH_AMBIGUOUS' for r in touched),
            'unresolved':sum(r['outcome']=='TOUCH_UNRESOLVED' for r in touched)}
    return {'version':'alpha-1.8.0-btc-4h-score-stratification',
       'asset':'BTC','timeframe':'4h','historical_closed_bars':len(bars),
       'lookback_bars':lookback,'horizon_bars':horizon,'stride_bars':stride,
       'score_bins_experimental':{'LOW':'score < 48','MEDIUM':'48 <= score < 60','HIGH':'score >= 60'},
       'groups':metrics,'events':events,
       'limitations':['4H_ONLY_NOT_MTF','SCORE_BANDS_UNCALIBRATED',
          'MULTIPLE_LEVELS_PER_DECISION_NOT_INDEPENDENT',
          'NO_TRAIN_VALIDATION_TEST_SPLIT','REJECTION_PROXY_NOT_VALIDATED',
          'HISTORICAL_REPLAY_NOT_EXECUTION_BACKTEST'],
       'research_only':True,'signals':[],'signals_enabled':False,'trading_enabled':False,
       'trade_authorized':False,'backtest_completed':False,
       'continuous_freshness_proven':False,'release_6_0_0_approved':False}

def main():
    report=evaluate(history_4h(pages=12))
    dest=Path('artifacts/alpha_swing_v180_btc_score_audit.json')
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V180',json.dumps({'groups':report['groups'],'trades':0,'signals':0}))
if __name__=='__main__':main()
