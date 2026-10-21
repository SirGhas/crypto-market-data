"""v1.9.3 mutually exclusive descriptive decision-window outcome categories."""
import json
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_decision_clusters_v192 import evaluate as clusters

def categorize(windows):
    totals={k:0 for k in ('rejection_only','breakout_only','both_rejection_and_breakout',
        'touch_without_confirmed_direction','no_touch')}
    for w in windows:
        reject=w['any_confirmed_rejection']; breakout=w['any_confirmed_breakout']; touch=w['any_touch']
        if (reject or breakout) and not touch:raise ValueError('CONFIRMATION_WITHOUT_TOUCH')
        if reject and breakout:key='both_rejection_and_breakout'
        elif reject:key='rejection_only'
        elif breakout:key='breakout_only'
        elif touch:key='touch_without_confirmed_direction'
        else:key='no_touch'
        totals[key]+=1
    if sum(totals.values())!=len(windows):raise ValueError('WINDOW_PARTITION_MISMATCH')
    return totals

def evaluate(bars):
    base=clusters(bars)
    windows=base['windows']
    totals=categorize(windows)
    if totals['rejection_only']+totals['both_rejection_and_breakout']!=base['decision_windows_with_any_confirmed_rejection']:
        raise ValueError('REJECTION_COUNT_MISMATCH')
    if totals['breakout_only']+totals['both_rejection_and_breakout']!=base['decision_windows_with_any_confirmed_breakout']:
        raise ValueError('BREAKOUT_COUNT_MISMATCH')
    if len(windows)-totals['no_touch']!=base['decision_windows_with_any_touch']:
        raise ValueError('TOUCH_COUNT_MISMATCH')
    return {'version':'alpha-1.9.3-btc-mutually-exclusive-window-outcomes',
      'asset':'BTC','timeframe':'4h','history_quality':base['history_quality'],
      'decision_windows_with_candidates':len(windows),'mutually_exclusive_window_counts':totals,
      'interpretation':'WINDOW_CATEGORIES_DESCRIPTIVE_NOT_TRADING_OPPORTUNITIES',
      'limitations':['DIFFERENT_LEVELS_IN_SAME_WINDOW_CAN_HAVE_DIFFERENT_OUTCOMES',
        'WINDOWS_NOT_INDEPENDENT_MARKET_EPISODES','NO_PREDICTIVE_VALIDATION',
        'NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v193_btc_exclusive_window_outcomes.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V193',json.dumps({'decision_windows':report['decision_windows_with_candidates'],
      'categories':report['mutually_exclusive_window_counts'],
      'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
