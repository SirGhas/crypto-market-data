"""v1.9.8: sensitivity audit of pre-decision ATR level-distance thresholds."""
import json
from decimal import Decimal,InvalidOperation
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_history_quality_v190 import audit
from engine.alpha_score_audit_v180 import evaluate as replay
from engine.alpha_atr_proximity_v197 import analyze

THRESHOLDS=(Decimal('0.1'),Decimal('0.25'),Decimal('0.5'),Decimal('0.75'),
            Decimal('1'),Decimal('1.5'),Decimal('2'))
def sensitivity(details):
    distances=[]
    for row in details:
        try:d=Decimal(str(row['nearest_pair_distance_atr']))
        except (InvalidOperation,ValueError,TypeError):raise ValueError('INVALID_ATR_DISTANCE')
        if not d.is_finite() or d<0:raise ValueError('INVALID_ATR_DISTANCE')
        distances.append(d)
    rows=[{'threshold_atr':str(t),'mixed_windows_within_threshold':sum(d<=t for d in distances),
      'mixed_windows_above_threshold':sum(d>t for d in distances)} for t in THRESHOLDS]
    if any(a['mixed_windows_within_threshold']>b['mixed_windows_within_threshold']
           for a,b in zip(rows,rows[1:])):raise ValueError('NON_MONOTONIC_COUNTS')
    return {'mixed_windows':len(distances),'threshold_sensitivity':rows}
def evaluate(bars):
    quality=audit(bars)
    events=replay(bars)['events']
    base=analyze(bars,events)
    result=sensitivity(base['details'])
    if result['mixed_windows']!=base['counts']['mixed_windows']:
        raise ValueError('MIXED_WINDOW_MISMATCH')
    return {'version':'alpha-1.9.8-btc-atr-threshold-sensitivity',
      'asset':'BTC','timeframe':'4h','history_quality':quality,**result,
      'atr_method':'PRE_DECISION_14_BAR_SIMPLE_TRUE_RANGE_MEAN',
      'interpretation':'DESCRIPTIVE_SENSITIVITY_NO_OPTIMAL_THRESHOLD_SELECTED',
      'limitations':['THRESHOLDS_EXPLORATORY','SINGLE_MARKET_AND_TIMEFRAME',
        'WINDOWS_NOT_INDEPENDENT','NO_PREDICTIVE_VALIDATION','NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v198_btc_atr_sensitivity.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V198',json.dumps({'mixed_windows':report['mixed_windows'],
      'threshold_sensitivity':report['threshold_sensitivity'],
      'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
