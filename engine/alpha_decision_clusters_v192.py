"""v1.9.2 descriptive decision-window clustering, not independent event counting."""
import json
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_history_quality_v190 import audit
from engine.alpha_score_audit_v180 import evaluate as replay

OUTCOMES=('NO_TOUCH','CONFIRMED_REJECTION','CONFIRMED_CLOSE_THROUGH','TOUCH_AMBIGUOUS','TOUCH_UNRESOLVED')
def evaluate(bars):
    quality=audit(bars)
    events=replay(bars)['events']
    grouped={}
    for e in events:
        epoch=e['decision_epoch']
        outcome=e['outcome']
        if outcome not in OUTCOMES:raise ValueError('INVALID_OUTCOME')
        if not isinstance(epoch,int) or isinstance(epoch,bool):raise ValueError('INVALID_DECISION_EPOCH')
        grouped.setdefault(epoch,[]).append(e)
    windows=[]
    for epoch,rows in sorted(grouped.items()):
        outcomes=[e['outcome'] for e in rows]
        windows.append({'decision_epoch':epoch,'level_observations':len(rows),
          'touched_level_observations':sum(x!='NO_TOUCH' for x in outcomes),
          'any_confirmed_rejection':('CONFIRMED_REJECTION' in outcomes),
          'any_confirmed_breakout':('CONFIRMED_CLOSE_THROUGH' in outcomes),
          'any_touch':any(x!='NO_TOUCH' for x in outcomes)})
    return {'version':'alpha-1.9.2-btc-decision-window-clusters',
      'asset':'BTC','timeframe':'4h','history_quality':quality,
      'level_observations':len(events),'decision_windows_with_candidates':len(windows),
      'decision_windows_with_any_touch':sum(w['any_touch'] for w in windows),
      'decision_windows_with_any_confirmed_rejection':sum(w['any_confirmed_rejection'] for w in windows),
      'decision_windows_with_any_confirmed_breakout':sum(w['any_confirmed_breakout'] for w in windows),
      'windows':windows,
      'interpretation':'WINDOW_COUNTS_REDUCE_LEVEL_DUPLICATION_NOT_INDEPENDENT_EPISODES',
      'limitations':['WINDOWS_CAN_SHARE_MARKET_REGIMES','SAME_LEVEL_CAN_RECUR',
        'MULTIPLE_OUTCOMES_PER_WINDOW','NO_PREDICTIVE_VALIDATION','NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    path=Path('artifacts/alpha_swing_v192_btc_decision_clusters.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V192',json.dumps({k:report[k] for k in (
      'level_observations','decision_windows_with_candidates',
      'decision_windows_with_any_touch','decision_windows_with_any_confirmed_rejection',
      'decision_windows_with_any_confirmed_breakout','signal_generation')}))
if __name__=='__main__':main()
