"""v2.0.3: exact structural level recurrence across BTC decision windows."""
import json
from collections import defaultdict
from decimal import Decimal,InvalidOperation
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_history_quality_v190 import audit
from engine.alpha_score_audit_v180 import evaluate as replay

def recurrence(events):
    identities=defaultdict(set)
    window_identities=defaultdict(set)
    for e in events:
        epoch=e['decision_epoch']
        side=e['side']
        if not isinstance(epoch,int) or isinstance(epoch,bool):raise ValueError('INVALID_EPOCH')
        if side not in ('support','resistance'):raise ValueError('INVALID_SIDE')
        try:price=Decimal(str(e['level']))
        except (InvalidOperation,ValueError,TypeError):raise ValueError('INVALID_LEVEL')
        if not price.is_finite() or price<=0:raise ValueError('INVALID_LEVEL')
        identity=(side,price.normalize())
        identities[identity].add(epoch)
        window_identities[epoch].add(identity)
    counts={'level_observations':len(events),'candidate_windows':len(window_identities),
      'unique_exact_level_identities':len(identities),
      'identities_in_multiple_windows':sum(len(v)>1 for v in identities.values()),
      'identities_in_three_or_more_windows':sum(len(v)>=3 for v in identities.values()),
      'windows_with_any_repeated_identity':0,
      'windows_with_identity_seen_in_prior_window':0,
      'consecutive_window_identity_links':0}
    repeated={key for key,epochs in identities.items() if len(epochs)>1}
    ordered=sorted(window_identities)
    for i,epoch in enumerate(ordered):
        current=window_identities[epoch]
        if current&repeated:counts['windows_with_any_repeated_identity']+=1
        if i:
            previous=window_identities[ordered[i-1]]
            shared=current&previous
            if shared:
                counts['windows_with_identity_seen_in_prior_window']+=1
                counts['consecutive_window_identity_links']+=len(shared)
    multiplicities=sorted(len(v) for v in identities.values())
    return {'counts':counts,
      'maximum_windows_per_exact_identity':multiplicities[-1] if multiplicities else 0,
      'identity_definition':'SIDE_PLUS_EXACT_NORMALIZED_DECIMAL_PRICE',
      'consecutive_definition':'ADJACENT_CANDIDATE_DECISION_WINDOWS_NOT_ADJACENT_CANDLES'}
def evaluate(bars):
    quality=audit(bars)
    result=recurrence(replay(bars)['events'])
    return {'version':'alpha-2.0.3-btc-exact-level-recurrence',
      'asset':'BTC','timeframe':'4h','history_quality':quality,**result,
      'interpretation':'EXACT_LEVEL_REUSE_AUDIT_NOT_INDEPENDENT_EPISODE_ESTIMATION',
      'limitations':['NEARBY_PRICE_LEVELS_NOT_MERGED','PRICE_IDENTITY_IS_NOT_ZONE_IDENTITY',
        'CONSECUTIVE_CANDIDATE_WINDOWS_MAY_BE_SEPARATED_IN_TIME',
        'NO_PREDICTIVE_VALIDATION','NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v203_btc_exact_level_recurrence.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V203',json.dumps({'counts':report['counts'],
      'maximum_windows_per_exact_identity':report['maximum_windows_per_exact_identity'],
      'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
