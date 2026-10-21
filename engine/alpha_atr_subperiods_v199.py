"""v1.9.9: chronological subperiod distribution of mixed-window ATR distances."""
import json
from decimal import Decimal,InvalidOperation
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_history_quality_v190 import audit
from engine.alpha_score_audit_v180 import evaluate as replay
from engine.alpha_atr_proximity_v197 import analyze
from engine.alpha_atr_sensitivity_v198 import THRESHOLDS

def split(details,parts=3):
    if not isinstance(parts,int) or isinstance(parts,bool) or parts<2:raise ValueError('INVALID_PARTS')
    ordered=sorted(details,key=lambda x:x['decision_epoch'])
    if len({d['decision_epoch'] for d in ordered})!=len(ordered):
        raise ValueError('DUPLICATE_DECISION_EPOCH')
    if len(ordered)<parts:raise ValueError('INSUFFICIENT_MIXED_WINDOWS')
    result=[]
    for i in range(parts):
        lo=i*len(ordered)//parts
        hi=(i+1)*len(ordered)//parts
        segment=ordered[lo:hi]
        distances=[]
        for item in segment:
            try:d=Decimal(str(item['nearest_pair_distance_atr']))
            except (InvalidOperation,ValueError,TypeError):raise ValueError('INVALID_ATR_DISTANCE')
            if not d.is_finite() or d<0:raise ValueError('INVALID_ATR_DISTANCE')
            distances.append(d)
        sorted_dist=sorted(distances)
        n=len(sorted_dist)
        result.append({'part':i+1,'first_decision_epoch':segment[0]['decision_epoch'],
          'last_decision_epoch':segment[-1]['decision_epoch'],'mixed_windows':n,
          'median_distance_atr':str(sorted_dist[(n-1)//2]) if n%2 else str((sorted_dist[n//2-1]+sorted_dist[n//2])/2),
          'min_distance_atr':str(sorted_dist[0]),'max_distance_atr':str(sorted_dist[-1]),
          'within_threshold_counts':{str(t):sum(d<=t for d in distances) for t in THRESHOLDS}})
    return result

def evaluate(bars):
    quality=audit(bars)
    base=analyze(bars,replay(bars)['events'])
    periods=split(base['details'])
    if sum(p['mixed_windows'] for p in periods)!=base['counts']['mixed_windows']:
        raise ValueError('PERIOD_SUM_MISMATCH')
    return {'version':'alpha-1.9.9-btc-mixed-atr-subperiod-distribution',
      'asset':'BTC','timeframe':'4h','history_quality':quality,
      'mixed_windows':base['counts']['mixed_windows'],'periods':periods,
      'partition_method':'EQUAL_COUNT_CHRONOLOGICAL_MIXED_WINDOWS_NOT_EQUAL_CALENDAR_DURATION',
      'interpretation':'DESCRIPTIVE_SUBPERIOD_DISTRIBUTION_NOT_REGIME_VALIDATION',
      'limitations':['SMALL_MIXED_WINDOW_SAMPLES','PERIODS_NOT_EQUAL_CALENDAR_DURATION',
        'SAME_MARKET_REGIME_MAY_SPAN_PERIODS','NO_PREDICTIVE_VALIDATION',
        'NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v199_btc_mixed_atr_subperiods.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V199',json.dumps({'mixed_windows':report['mixed_windows'],
      'periods':report['periods'],'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
