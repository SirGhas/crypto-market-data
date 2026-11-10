"""v2.0.8: independently replay a retained snapshot from a different Actions run."""
import argparse
import json
from pathlib import Path
from engine.alpha_offline_replay_v207 import evaluate as offline_evaluate

def verify(snapshot_path, source_report_path, expected_sha256, source_run_id, current_run_id, source_replay_path):
    if not str(source_run_id).isdigit() or not str(current_run_id).isdigit():
        raise ValueError('RUN_ID_REQUIRED')
    if str(source_run_id) == str(current_run_id):
        raise ValueError('SOURCE_RUN_MUST_BE_INDEPENDENT')
    source = json.loads(Path(source_report_path).read_text(encoding='utf-8'))
    if source.get('snapshot_file_sha256') != expected_sha256:
        raise ValueError('SOURCE_SNAPSHOT_DIGEST_MISMATCH')
    replay = offline_evaluate(snapshot_path, expected_sha256)
    if replay['event_count'] != source.get('replay_event_count'):
        raise ValueError('CROSS_RUN_EVENT_COUNT_MISMATCH')
    if replay['recurrence_counts'] != source.get('recurrence_counts'):
        raise ValueError('CROSS_RUN_RECURRENCE_MISMATCH')
    if replay['history_quality'] != source.get('history_quality'):
        raise ValueError('CROSS_RUN_HISTORY_MISMATCH')
    source_replay = json.loads(Path(source_replay_path).read_text(encoding='utf-8'))
    if source_replay.get('snapshot_file_sha256') != expected_sha256:
        raise ValueError('SOURCE_REPLAY_DIGEST_MISMATCH')
    if replay['gap_counts'] != source_replay.get('gap_counts'):
        raise ValueError('CROSS_RUN_GAP_COUNTS_MISMATCH')
    return {
        'version': 'alpha-2.0.8-cross-run-offline-replay',
        'source_run_id': str(source_run_id),
        'replay_run_id': str(current_run_id),
        'snapshot_digest': expected_sha256,
        'event_count': replay['event_count'],
        'recurrence_counts': replay['recurrence_counts'],
        'gap_counts': replay['gap_counts'],
        'cross_run_verified': True,
        'research_only': True,
        'signals': [],
        'backtest_completed': False,
        'continuous_freshness_proven': False,
        'signals_enabled': False,
        'trading_enabled': False,
        'trade_authorized': False,
        'release_6_0_0_approved': False,
        'signal_generation': {'status': 'DISABLED_BY_SAFETY_POLICY', 'generated_signals': None},
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--source-report', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--source-run-id', required=True)
    parser.add_argument('--current-run-id', required=True)
    parser.add_argument('--source-replay', required=True)
    args = parser.parse_args()
    result = verify(args.snapshot, args.source_report, args.sha256,
                    args.source_run_id, args.current_run_id, args.source_replay)
    out = Path('artifacts/alpha_swing_v208_cross_run_replay.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('ALPHA_V208', json.dumps(result))

if __name__ == '__main__':
    main()
