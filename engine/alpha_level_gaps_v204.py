"""v2.0.4: time gaps between exact structural-level appearances."""
import json
from collections import defaultdict
from decimal import Decimal,InvalidOperation
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_history_quality_v190 import audit
from engine.alpha_score_audit_v180 import evaluate as replay
from engine.alpha_level_recurrence_v203 import recurrence

STEP=14400
def gaps(events):
    identities=defaultdict(set)
    for e in events:
        epoch=e['decision_epoch'];side=e['side']
        if not isinstance(epoch,int) or isinstance(epoch,bool):raise ValueError('INVALID_EPOCH')
        if side not in ('support','resistance'):raise ValueError('INVALID_SIDE')
        try:price=Decimal(str(e['level']))
        except (InvalidOperation,ValueError,TypeError):raise ValueError('INVALID_LEVEL')
        if not price.is_finite() or price<=0:raise ValueError('INVALID_LEVEL')
        identities[(side,price.normalize())].add(epoch)
    intervals=[]
    for epochs in identities.values():
        ordered=sorted(epochs)
        for a,b in zip(ordered,ordered[1:]):
            if b<=a or (b-a)%STEP:raise ValueError('INVALID_GAP_ALIGNMENT')
            intervals.append((b-a)//STEP)
    n=len(intervals)
    groups={'up_to_12_bars':sum(v<=12 for v in intervals),
      '13_to_36_bars':sum(12<v<=36 for v in intervals),
      '37_to_72_bars':sum(36<v<=72 for v in intervals),
      'above_72_bars':sum(v>72 for v in intervals)}
    if sum(groups.values())!=n:raise ValueError('GAP_RECONCILIATION_FAILED')
    ordered=sorted(intervals)
    median=(ordered[(n-1)//2] if n%2 else (ordered[n//2-1]+ordered[n//2])/2) if n else None
    return {'repeated_exact_identities':sum(len(v)>1 for v in identities.values()),
      'between_appearance_intervals':n,'gap_buckets_4h_bars':groups,
      'median_gap_4h_bars':median,'max_gap_4h_bars':max(intervals) if n else None,
      'gap_definition':'CONSECUTIVE_APPEARANCES_OF_SAME_SIDE_AND_EXACT_PRICE'}
def evaluate(bars):
    quality=audit(bars)
    events=replay(bars)['events']
    result=gaps(events)
    reference=recurrence(events)
    if result['repeated_exact_identities']!=reference['counts']['identities_in_multiple_windows']:
        raise ValueError('RECURRENCE_COUNT_MISMATCH')
    return {'version':'alpha-2.0.4-btc-exact-level-reappearance-gaps',
      'asset':'BTC','timeframe':'4h','history_quality':quality,**result,
      'interpretation':'DESCRIPTIVE_REAPPEARANCE_GAPS_NOT_INDEPENDENT_MARKET_EPISODES',
      'limitations':['EXACT_PRICE_NOT_PRICE_ZONE','GAP_NOT_EVIDENCE_OF_CAUSAL_INDEPENDENCE',
        'CANDIDATE_SELECTION_MAY_CHANGE','NO_PREDICTIVE_VALIDATION',
        'NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v204_btc_exact_level_gaps.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V204',json.dumps({'repeated_exact_identities':report['repeated_exact_identities'],
      'between_appearance_intervals':report['between_appearance_intervals'],
      'gap_buckets_4h_bars':report['gap_buckets_4h_bars'],
      'median_gap_4h_bars':report['median_gap_4h_bars'],
      'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
