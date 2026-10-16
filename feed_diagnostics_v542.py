"""Compact, non-sensitive diagnostics for unavailable market feeds (v5.4.2)."""
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def main(argv):
    if len(argv) != 3:
        print('Usage: python feed_diagnostics_v542.py <multisource.json> <diagnostics.json>', file=sys.stderr)
        return 2
    source, target = map(Path, argv[1:])
    try:
        data = json.loads(source.read_text(encoding='utf-8'))
        pairs = data['pairs']
        unavailable = {}
        sources = Counter()
        for symbol, pair in sorted(pairs.items()):
            for timeframe, frame in sorted(pair.get('frames', {}).items()):
                key = f'{symbol}:{timeframe}'
                if frame.get('status') == 'available':
                    sources[frame.get('source', 'UNKNOWN')] += 1
                else:
                    unavailable[key] = {'status': frame.get('status', 'missing'),
                                        'errors': frame.get('errors', ['missing_frame'])}
        report = {'schema_version': '5.4.2',
                  'generated_at_utc': datetime.now(timezone.utc).isoformat(),
                  'snapshot_generated_at_utc': data.get('generated_at_utc'),
                  'summary': {'attempted': sum(sources.values()) + len(unavailable),
                              'available': sum(sources.values()),
                              'unavailable': len(unavailable),
                              'available_by_source': dict(sources)},
                  'unavailable_feeds': unavailable,
                  'limitations': ['Diagnostic only; no trades or signals',
                                  'Does not independently verify exchange provenance']}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report['summary']))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Diagnostic generation failed: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
