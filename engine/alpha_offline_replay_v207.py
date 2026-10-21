"""v2.0.7: offline BTC research replay from a verified frozen JSON snapshot."""
import argparse,hashlib,json
from decimal import Decimal,InvalidOperation
from pathlib import Path
from engine.alpha_history_quality_v190 import audit
from engine.alpha_snapshot_repro_v205 import reconcile
from engine.alpha_archive_v206 import archive

def load_snapshot(path,expected_sha256):
    if not isinstance(expected_sha256,str) or len(expected_sha256)!=64 or any(c not in '0123456789abcdef' for c in expected_sha256):
        raise ValueError('EXPECTED_SHA256_REQUIRED')
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw.rstrip(b'\n')).hexdigest()!=expected_sha256:
        raise ValueError('SNAPSHOT_SHA256_MISMATCH')
    try:payload=json.loads(raw)
    except (ValueError,UnicodeDecodeError):raise ValueError('INVALID_SNAPSHOT_JSON')
    if not isinstance(payload,dict) or payload.get('schema')!='btc-4h-ohlcv-snapshot-v1':
        raise ValueError('INVALID_SNAPSHOT_SCHEMA')
    if payload.get('asset')!='BTC' or payload.get('timeframe')!='4h' or payload.get('source')!='OKX BTC-USDT 4H history-candles':
        raise ValueError('INVALID_SNAPSHOT_IDENTITY')
    try:
        bars=[tuple([row[0]]+[Decimal(v) for v in row[1:]]) for row in payload['bars']]
    except (KeyError,TypeError,InvalidOperation,ValueError,IndexError):
        raise ValueError('INVALID_SNAPSHOT_BARS')
    quality=audit(bars)
    if quality!=payload.get('history_quality'):raise ValueError('SNAPSHOT_PROVENANCE_MISMATCH')
    rebuilt,canonical_sha=archive(bars)
    if rebuilt!=payload or canonical_sha!=expected_sha256:
        raise ValueError('NONCANONICAL_SNAPSHOT')
    return bars,quality

def evaluate(path,sha256):
    bars,quality=load_snapshot(path,sha256)
    replay=reconcile(bars)
    if replay['history_quality']!=quality:raise ValueError('OFFLINE_REPLAY_PROVENANCE_MISMATCH')
    return {'version':'alpha-2.0.7-btc-offline-verified-replay',
      'asset':'BTC','timeframe':'4h','history_quality':quality,
      'snapshot_file_sha256':sha256,'event_count':replay['event_count'],
      'recurrence_counts':replay['recurrence_counts'],
      'gap_counts':replay['gap_counts'],'offline_replay_verified':True,
      'interpretation':'OFFLINE_REPRODUCIBILITY_NOT_PREDICTIVE_VALIDATION',
      'limitations':['INPUT_SNAPSHOT_MUST_BE_RETAINED','SINGLE_DATA_PROVIDER',
        'NO_CROSS_PROVIDER_VERIFICATION','NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    parser=argparse.ArgumentParser(description='Offline verified BTC 4h snapshot replay')
    parser.add_argument('--snapshot',required=True)
    parser.add_argument('--sha256',required=True)
    args=parser.parse_args()
    report=evaluate(args.snapshot,args.sha256)
    p=Path('artifacts/alpha_swing_v207_btc_offline_replay.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V207',json.dumps({'event_count':report['event_count'],
      'snapshot_file_sha256':report['snapshot_file_sha256'],
      'offline_replay_verified':report['offline_replay_verified'],
      'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
