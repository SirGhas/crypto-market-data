"""v1.9.4: explain mixed-outcome windows by support/resistance side."""
import json
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_history_quality_v190 import audit
from engine.alpha_score_audit_v180 import evaluate as replay
from engine.alpha_window_outcomes_v193 import categorize

SIDES=('support','resistance')
OUTCOMES=('NO_TOUCH','CONFIRMED_REJECTION','CONFIRMED_CLOSE_THROUGH','TOUCH_AMBIGUOUS','TOUCH_UNRESOLVED')
def analyze(events):
    windows={}
    for e in events:
        side=e['side']; outcome=e['outcome']; epoch=e['decision_epoch']
        if side not in SIDES:raise ValueError('INVALID_SIDE')
        if outcome not in OUTCOMES:raise ValueError('INVALID_OUTCOME')
        if not isinstance(epoch,int) or isinstance(epoch,bool):raise ValueError('INVALID_EPOCH')
        windows.setdefault(epoch,[]).append(e)
    descriptors=[];mixed_details={'mixed_windows':0,'mixed_across_sides':0,
       'mixed_within_support':0,'mixed_within_resistance':0}
    for epoch,rows in sorted(windows.items()):
        sides={s:{'rejection':any(e['side']==s and e['outcome']=='CONFIRMED_REJECTION' for e in rows),
                  'breakout':any(e['side']==s and e['outcome']=='CONFIRMED_CLOSE_THROUGH' for e in rows)}
               for s in SIDES}
        rejection=any(sides[s]['rejection'] for s in SIDES)
        breakout=any(sides[s]['breakout'] for s in SIDES)
        touch=any(e['outcome']!='NO_TOUCH' for e in rows)
        descriptors.append({'decision_epoch':epoch,'any_touch':touch,
          'any_confirmed_rejection':rejection,'any_confirmed_breakout':breakout})
        if rejection and breakout:
            mixed_details['mixed_windows']+=1
            if any(sides[a]['rejection'] and sides[b]['breakout'] for a in SIDES for b in SIDES if a!=b):
                mixed_details['mixed_across_sides']+=1
            for s in SIDES:
                if sides[s]['rejection'] and sides[s]['breakout']:
                    mixed_details['mixed_within_'+s]+=1
    categories=categorize(descriptors)
    if categories['both_rejection_and_breakout']!=mixed_details['mixed_windows']:
        raise ValueError('MIXED_COUNT_MISMATCH')
    return {'decision_windows':len(descriptors),'categories':categories,
      'mixed_outcome_details':mixed_details}
def evaluate(bars):
    quality=audit(bars)
    result=analyze(replay(bars)['events'])
    return {'version':'alpha-1.9.4-btc-mixed-outcome-side-audit',
      'asset':'BTC','timeframe':'4h','history_quality':quality,**result,
      'interpretation':'MIXED_CATEGORIES_OVERLAP_AND_ARE_NOT_ADDITIVE',
      'limitations':['SAME_SIDE_MAY_CONTAIN_MULTIPLE_LEVELS',
        'WINDOWS_NOT_INDEPENDENT','NO_TRADE_FLOW_VALIDATION',
        'NO_PREDICTIVE_VALIDATION','NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v194_btc_mixed_outcome_sides.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V194',json.dumps({'decision_windows':report['decision_windows'],
      'categories':report['categories'],'mixed_outcome_details':report['mixed_outcome_details'],
      'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
