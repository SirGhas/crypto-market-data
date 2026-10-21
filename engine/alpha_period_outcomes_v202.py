"""v2.0.2: equal-duration window outcome rates with consistent denominators."""
import json
from decimal import Decimal
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_equal_duration_v200 import evaluate as duration_evaluate
from engine.alpha_decision_clusters_v192 import evaluate as clusters
from engine.alpha_window_outcomes_v193 import categorize

def partition(windows,periods):
    keys=('rejection_only','breakout_only','both_rejection_and_breakout',
          'touch_without_confirmed_direction','no_touch')
    result=[]
    all_epochs=set()
    for p in periods:
        start,end=p['start_epoch_inclusive'],p['end_epoch_exclusive']
        selected=[w for w in windows if start<=w['decision_epoch']<end]
        if len(selected)!=p['candidate_decision_windows']:
            raise ValueError('PERIOD_DENOMINATOR_MISMATCH')
        for w in selected:
            if w['decision_epoch'] in all_epochs:raise ValueError('DUPLICATE_WINDOW')
            all_epochs.add(w['decision_epoch'])
        n=len(selected)
        if not n:raise ValueError('EMPTY_CANDIDATE_PERIOD')
        counts=categorize(selected)
        touch=n-counts['no_touch']
        reject=counts['rejection_only']+counts['both_rejection_and_breakout']
        breakout=counts['breakout_only']+counts['both_rejection_and_breakout']
        metrics={'any_touch':touch,'any_confirmed_rejection':reject,
                 'any_confirmed_breakout':breakout,'mixed_rejection_and_breakout':counts['both_rejection_and_breakout']}
        result.append({'part':p['part'],'candidate_decision_windows':n,
          'exclusive_outcomes':counts,
          'overlapping_event_window_counts':metrics,
          'event_window_share_pct':{k:str((Decimal(v)*100/Decimal(n)).quantize(Decimal('0.01')))
             for k,v in metrics.items()},
          'exclusive_outcome_share_pct':{k:str((Decimal(counts[k])*100/Decimal(n)).quantize(Decimal('0.01')))
             for k in keys}})
    if len(all_epochs)!=len(windows):raise ValueError('WINDOW_COVERAGE_MISMATCH')
    return result

def evaluate(bars):
    duration=duration_evaluate(bars)
    cluster=clusters(bars)
    periods=partition(cluster['windows'],duration['equal_duration_periods'])
    if sum(p['exclusive_outcomes']['both_rejection_and_breakout'] for p in periods)!=duration['mixed_windows']:
        raise ValueError('MIXED_RECONCILIATION_MISMATCH')
    return {'version':'alpha-2.0.2-btc-period-window-outcome-rates',
      'asset':'BTC','timeframe':'4h','history_quality':duration['history_quality'],
      'periods':periods,'denominator':'ALL_CANDIDATE_DECISION_WINDOWS_PER_EQUAL_DURATION_PERIOD',
      'interpretation':'DESCRIPTIVE_WINDOW_EVENT_FREQUENCY_NOT_TRADE_SUCCESS_RATE',
      'limitations':['OVERLAPPING_EVENT_METRICS_NOT_ADDITIVE',
        'WINDOWS_NOT_INDEPENDENT','NO_PREDICTIVE_VALIDATION','NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v202_btc_period_outcome_rates.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V202',json.dumps({'periods':report['periods'],
      'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
