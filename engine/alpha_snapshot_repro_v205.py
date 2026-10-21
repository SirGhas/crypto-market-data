"""v2.0.5: reproducibility and provenance reconciliation on one immutable BTC bar set."""
import json
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_history_quality_v190 import audit
from engine.alpha_score_audit_v180 import evaluate as replay
from engine.alpha_level_recurrence_v203 import recurrence
from engine.alpha_level_gaps_v204 import gaps

def reconcile(bars):
    first=audit(bars)
    events1=replay(bars)['events']
    events2=replay(bars)['events']
    if events1!=events2:raise ValueError('NONDETERMINISTIC_EVENT_REPLAY')
    rec1=recurrence(events1)
    rec2=recurrence(events2)
    gap1=gaps(events1)
    gap2=gaps(events2)
    if rec1!=rec2 or gap1!=gap2:raise ValueError('NONDETERMINISTIC_SUMMARY')
    if gap1['repeated_exact_identities']!=rec1['counts']['identities_in_multiple_windows']:
        raise ValueError('REPEATED_IDENTITY_MISMATCH')
    if rec1['counts']['level_observations']!=len(events1):
        raise ValueError('LEVEL_OBSERVATION_MISMATCH')
    if first!=audit(bars):raise ValueError('MUTATED_HISTORY')
    return {'history_quality':first,'event_count':len(events1),
      'replay_deterministic':True,'summary_deterministic':True,
      'recurrence_counts':rec1['counts'],'gap_counts':gap1,
      'data_comparison_policy':'CROSS_RUN_COUNTS_REQUIRE_MATCHING_SHA256_AND_WINDOW_BOUNDS',
      'single_input_provenance':'ONE_HISTORY_FETCH_REUSED_FOR_BOTH_REPLAYS'}
def evaluate(bars):
    result=reconcile(bars)
    return {'version':'alpha-2.0.5-btc-snapshot-reproducibility',
      'asset':'BTC','timeframe':'4h',**result,
      'interpretation':'SAME_INPUT_REPRODUCIBILITY_NOT_CROSS_RUN_DATA_EQUIVALENCE',
      'limitations':['NO_PERSISTENT_HISTORY_ARCHIVE','NO_CROSS_PROVIDER_VERIFICATION',
        'NO_CROSS_RUN_SHA_COMPARISON','NO_PREDICTIVE_VALIDATION','NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v205_btc_snapshot_reproducibility.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V205',json.dumps({'history_quality':report['history_quality'],
      'event_count':report['event_count'],
      'replay_deterministic':report['replay_deterministic'],
      'recurrence_counts':report['recurrence_counts'],
      'gap_intervals':report['gap_counts']['between_appearance_intervals'],
      'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
