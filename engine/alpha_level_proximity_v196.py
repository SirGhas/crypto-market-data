"""v1.9.6 descriptive price-proximity audit of mixed-outcome level pairs."""
import json
from collections import defaultdict
from decimal import Decimal,InvalidOperation
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_history_quality_v190 import audit
from engine.alpha_score_audit_v180 import evaluate as replay
from engine.alpha_level_identity_v195 import summarize

R='CONFIRMED_REJECTION';B='CONFIRMED_CLOSE_THROUGH'
THRESHOLDS=(Decimal('0.001'),Decimal('0.005'),Decimal('0.01'))
def proximity(events):
    windows=defaultdict(list)
    for e in events:
        if e['outcome'] not in (R,B):continue
        if e['side'] not in ('support','resistance'):raise ValueError('INVALID_SIDE')
        try:p=Decimal(str(e['level']))
        except (InvalidOperation,ValueError,TypeError):raise ValueError('INVALID_LEVEL')
        if not p.is_finite() or p<=0:raise ValueError('INVALID_LEVEL')
        epoch=e['decision_epoch']
        if not isinstance(epoch,int) or isinstance(epoch,bool):raise ValueError('INVALID_EPOCH')
        windows[epoch].append((e['side'],p,e['outcome']))
    counts={'mixed_windows':0,'same_side_nearest_pair_windows':0,
       'opposite_side_nearest_pair_windows':0}
    for threshold in THRESHOLDS:
        counts['mixed_windows_with_pair_within_'+str(threshold*100)+'pct']=0
    distances=[]
    for epoch,rows in sorted(windows.items()):
        rejects={(s,p) for s,p,o in rows if o==R}
        breaks={(s,p) for s,p,o in rows if o==B}
        if not rejects or not breaks:continue
        counts['mixed_windows']+=1
        pairs=[(abs(a[1]-b[1])/((a[1]+b[1])/2),a[0]==b[0]) for a in rejects for b in breaks]
        distance,same_side=min(pairs,key=lambda x:x[0])
        distances.append({'decision_epoch':epoch,'nearest_relative_distance_pct':str((distance*100).normalize()),
          'nearest_pair_same_side':same_side})
        counts['same_side_nearest_pair_windows' if same_side else 'opposite_side_nearest_pair_windows']+=1
        for threshold in THRESHOLDS:
            if distance<=threshold:
                counts['mixed_windows_with_pair_within_'+str(threshold*100)+'pct']+=1
    return {'counts':counts,'mixed_window_distances':distances}
def evaluate(bars):
    quality=audit(bars)
    events=replay(bars)['events']
    base=summarize(events)
    details=proximity(events)
    if details['counts']['mixed_windows']!=base['mixed_windows']:
        raise ValueError('MIXED_WINDOW_MISMATCH')
    return {'version':'alpha-1.9.6-btc-mixed-level-proximity-audit',
      'asset':'BTC','timeframe':'4h','history_quality':quality,
      'exact_identity_conflicts':base['mixed_with_same_level_identity'],
      **details,'distance_definition':'ABS_PRICE_DIFFERENCE_DIVIDED_BY_PAIR_MIDPOINT',
      'interpretation':'DESCRIPTIVE_PRICE_PROXIMITY_NOT_ZONE_EQUIVALENCE',
      'limitations':['THRESHOLDS_EXPLORATORY_NOT_ATR_NORMALIZED',
        'NEAREST_PAIR_MAY_NOT_EXPLAIN_CAUSAL_OUTCOME',
        'WINDOWS_NOT_INDEPENDENT','NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v196_btc_mixed_level_proximity.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V196',json.dumps({'counts':report['counts'],
      'exact_identity_conflicts':report['exact_identity_conflicts'],
      'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
