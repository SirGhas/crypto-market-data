"""v2.0.6: immutable per-run BTC OHLCV snapshot with provenance and replay verification."""
import json,hashlib
from decimal import Decimal
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_history_quality_v190 import audit
from engine.alpha_snapshot_repro_v205 import reconcile

def archive(bars):
    quality=audit(bars)
    canonical=[[b[0]]+[str(Decimal(str(v))) for v in b[1:]] for b in bars]
    payload={'schema':'btc-4h-ohlcv-snapshot-v1','source':'OKX BTC-USDT 4H history-candles',
      'asset':'BTC','timeframe':'4h','history_quality':quality,'bars':canonical}
    parsed=[tuple([b[0]]+[Decimal(v) for v in b[1:]]) for b in payload['bars']]
    if audit(parsed)!=quality:raise ValueError('SNAPSHOT_ROUNDTRIP_MISMATCH')
    encoded=json.dumps(payload,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode('utf-8')
    return payload,hashlib.sha256(encoded).hexdigest()

def evaluate(bars):
    payload,digest=archive(bars)
    replay=reconcile(bars)
    if replay['history_quality']!=payload['history_quality']:
        raise ValueError('REPLAY_PROVENANCE_MISMATCH')
    return {'version':'alpha-2.0.6-btc-archived-research-snapshot',
      'history_quality':payload['history_quality'],'snapshot_file_sha256':digest,
      'replay_deterministic':replay['replay_deterministic'],
      'replay_event_count':replay['event_count'],
      'recurrence_counts':replay['recurrence_counts'],
      'interpretation':'PER_RUN_RETRIEVABLE_ARTIFACT_NOT_PERMANENT_ARCHIVE',
      'limitations':['GITHUB_ARTIFACT_RETENTION_14_DAYS','SINGLE_DATA_PROVIDER',
        'SNAPSHOT_NOT_EXTERNALLY_SIGNED','NO_PREDICTIVE_VALIDATION','NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    bars=history_4h(pages=12)
    payload,digest=archive(bars)
    report=evaluate(bars)
    if digest!=report['snapshot_file_sha256']:raise ValueError('SNAPSHOT_DIGEST_MISMATCH')
    dest=Path('artifacts');dest.mkdir(parents=True,exist_ok=True)
    (dest/'alpha_swing_v206_btc_4h_snapshot.json').write_text(
      json.dumps(payload,ensure_ascii=False,separators=(',',':'),sort_keys=True)+'\n',encoding='utf-8')
    (dest/'alpha_swing_v206_btc_snapshot_report.json').write_text(
      json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V206',json.dumps({'history_quality':report['history_quality'],
      'snapshot_file_sha256':digest,'replay_event_count':report['replay_event_count'],
      'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
