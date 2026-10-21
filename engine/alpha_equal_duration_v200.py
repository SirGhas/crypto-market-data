"""v2.0.0: equal-duration chronological sensitivity audit, research only."""
import json
from decimal import Decimal
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_history_quality_v190 import audit
from engine.alpha_score_audit_v180 import evaluate as replay
from engine.alpha_atr_proximity_v197 import analyze
from engine.alpha_atr_subperiods_v199 import split
from engine.alpha_atr_sensitivity_v198 import THRESHOLDS

def equal_duration(details,decision_epochs,parts=3):
    if not isinstance(parts,int) or isinstance(parts,bool) or parts<2:raise ValueError('INVALID_PARTS')
    if not decision_epochs:raise ValueError('NO_DECISION_WINDOWS')
    if any(not isinstance(t,int) or isinstance(t,bool) for t in decision_epochs):
        raise ValueError('INVALID_EPOCH')
    epochs=sorted(set(decision_epochs))
    start,end=epochs[0],epochs[-1]
    if end<=start:raise ValueError('INSUFFICIENT_TIMESPAN')
    if len({d['decision_epoch'] for d in details})!=len(details):
        raise ValueError('DUPLICATE_MIXED_EPOCH')
    if any(d['decision_epoch'] not in epochs for d in details):
        raise ValueError('MIXED_OUTSIDE_DECISIONS')
    result=[]
    for i in range(parts):
        lo=start+(end-start+1)*i//parts
        hi=start+(end-start+1)*(i+1)//parts
        segment=[d for d in details if lo<=d['decision_epoch']<hi]
        dists=[Decimal(str(d['nearest_pair_distance_atr'])) for d in segment]
        if any(not d.is_finite() or d<0 for d in dists):
            raise ValueError('INVALID_ATR_DISTANCE')
        ordered=sorted(dists)
        n=len(ordered)
        median=(ordered[(n-1)//2] if n%2 else (ordered[n//2-1]+ordered[n//2])/2) if n else None
        result.append({'part':i+1,'start_epoch_inclusive':lo,'end_epoch_exclusive':hi,
          'candidate_decision_windows':sum(lo<=t<hi for t in epochs),
          'mixed_windows':n,'median_distance_atr':str(median) if median is not None else None,
          'within_threshold_counts':{str(t):sum(d<=t for d in dists) for t in THRESHOLDS}})
    if sum(p['mixed_windows'] for p in result)!=len(details):
        raise ValueError('PERIOD_RECONCILIATION_FAILED')
    if sum(p['candidate_decision_windows'] for p in result)!=len(epochs):
        raise ValueError('DECISION_RECONCILIATION_FAILED')
    return result

def evaluate(bars):
    quality=audit(bars)
    events=replay(bars)['events']
    base=analyze(bars,events)
    epochs=[e['decision_epoch'] for e in events]
    calendar=equal_duration(base['details'],epochs)
    count=split(base['details'])
    return {'version':'alpha-2.0.0-btc-equal-duration-subperiod-audit',
      'asset':'BTC','timeframe':'4h','history_quality':quality,
      'mixed_windows':base['counts']['mixed_windows'],
      'equal_duration_periods':calendar,
      'equal_mixed_count_periods':count,
      'partition_method':'THREE_EQUAL_EPOCH_SPANS_ACROSS_ALL_CANDIDATE_DECISION_WINDOWS',
      'interpretation':'DESCRIPTIVE_PARTITION_SENSITIVITY_NOT_PREDICTIVE_VALIDATION',
      'limitations':['SMALL_MIXED_WINDOW_SAMPLES','NO_REGIME_INDEPENDENCE',
        'ATR_LOOKBACK_FIXED_14','NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v200_btc_equal_duration_subperiods.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V200',json.dumps({'mixed_windows':report['mixed_windows'],
      'equal_duration_periods':report['equal_duration_periods'],
      'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
