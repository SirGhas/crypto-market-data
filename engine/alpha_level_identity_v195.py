"""v1.9.5: inspect conflicting historical outcomes at identical level identities."""
import json
from collections import defaultdict
from pathlib import Path
from decimal import Decimal,InvalidOperation
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_history_quality_v190 import audit
from engine.alpha_score_audit_v180 import evaluate as replay

REJECTION='CONFIRMED_REJECTION'
BREAKOUT='CONFIRMED_CLOSE_THROUGH'
OUTCOMES={'NO_TOUCH',REJECTION,BREAKOUT,'TOUCH_AMBIGUOUS','TOUCH_UNRESOLVED'}
def summarize(events):
    by_window=defaultdict(list)
    for e in events:
        epoch=e['decision_epoch'];side=e['side'];outcome=e['outcome']
        if not isinstance(epoch,int) or isinstance(epoch,bool):raise ValueError('INVALID_EPOCH')
        if side not in ('support','resistance'):raise ValueError('INVALID_SIDE')
        if outcome not in OUTCOMES:raise ValueError('INVALID_OUTCOME')
        try:price=Decimal(str(e['level']))
        except (InvalidOperation,ValueError,TypeError):raise ValueError('INVALID_LEVEL')
        if not price.is_finite() or price<=0:raise ValueError('INVALID_LEVEL')
        by_window[epoch].append((side,price.normalize(),outcome))
    mixed_windows=0;same_identity_conflicts=0;different_identity_mixed=0
    mixed_details=[]
    for epoch,rows in sorted(by_window.items()):
        rejects={(side,price) for side,price,o in rows if o==REJECTION}
        breaks={(side,price) for side,price,o in rows if o==BREAKOUT}
        if rejects and breaks:
            mixed_windows+=1
            shared=rejects&breaks
            if shared:same_identity_conflicts+=1
            else:different_identity_mixed+=1
            mixed_details.append({'decision_epoch':epoch,
                'same_level_conflict':bool(shared),
                'conflicting_level_identities':len(shared),
                'distinct_rejection_level_identities':len(rejects),
                'distinct_breakout_level_identities':len(breaks)})
    if mixed_windows!=same_identity_conflicts+different_identity_mixed:
        raise ValueError('MIXED_PARTITION_MISMATCH')
    return {'decision_windows_with_candidates':len(by_window),
      'mixed_windows':mixed_windows,
      'mixed_with_same_level_identity':same_identity_conflicts,
      'mixed_only_across_different_level_identities':different_identity_mixed,
      'mixed_window_details':mixed_details}
def evaluate(bars):
    quality=audit(bars)
    result=summarize(replay(bars)['events'])
    return {'version':'alpha-1.9.5-btc-level-identity-conflict-audit',
      'asset':'BTC','timeframe':'4h','history_quality':quality,**result,
      'level_identity':'EXACT_NORMALIZED_DECIMAL_PRICE_PLUS_SUPPORT_OR_RESISTANCE',
      'interpretation':'EXACT_IDENTITY_COMPARISON_NOT_PRICE_ZONE_DEDUPLICATION',
      'limitations':['NEARBY_PRICE_LEVELS_ARE_NOT_MERGED',
        'SAME_IDENTITY_CAN_HAVE_MULTIPLE_OBSERVATIONS',
        'WINDOWS_NOT_INDEPENDENT','NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v195_btc_level_identity_conflicts.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V195',json.dumps({k:report[k] for k in (
      'decision_windows_with_candidates','mixed_windows',
      'mixed_with_same_level_identity','mixed_only_across_different_level_identities',
      'signal_generation')}))
if __name__=='__main__':main()
