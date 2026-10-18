"""Idempotent, fail-closed ZEC integration patch for known crypto-market-data files."""
import argparse
from pathlib import Path

TARGETS = {
    'multisource_collector.py': 'COINS=',
    'dual_screen_v53.py': 'COINS =',
    'event_engine_v52.py': 'SYMBOLS =',
    'report_v51.py': 'COINS=',
    'event_aligned_v598.py': 'COINS=',
}

def patch_tuple(source, marker):
    lines = source.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if line.startswith(marker)]
    if len(matches) != 1:
        raise ValueError(f'expected one {marker!r} tuple, got {len(matches)}')
    i = matches[0]
    line = lines[i]
    if "'ZEC'" in line:
        return source
    if "'AAVE'" not in line or ')' not in line:
        raise ValueError('unexpected coin tuple; manual review required')
    lines[i] = line.replace("'AAVE'", "'AAVE','ZEC'", 1)
    return ''.join(lines)

ZEC_GUARD = '''        # ZEC: fail closed unless its BTC cross is directly sourced from OKX Spot.
        # Never infer independent cross validity from a fallback or derived series.
        if coin == 'ZEC':
            cross = market.get('pairs', {}).get('ZECBTC', {}).get('frames', {}).get('4h', {})
            if cross.get('source') != 'OKX Spot' or cross.get('status') != 'available':
                errors.append('zec_btc_cross_not_verified_okx')
            else:
                cs = cross.get('candles', [])
                if not isinstance(cs, list) or len(cs) < 233:
                    errors.append('zec_btc_cross_insufficient_history')
                else:
                    try:
                        stamps = [int(c['t']) for c in cs[-233:]]
                        if any(b - a != 14400 for a, b in zip(stamps, stamps[1:])) or not 0 <= now - (stamps[-1] + 14400) <= 14700:
                            errors.append('zec_btc_cross_stale_or_gapped')
                    except (KeyError, TypeError, ValueError):
                        errors.append('zec_btc_cross_invalid')
'''

def patch_guard(source):
    if 'zec_btc_cross_not_verified_okx' in source:
        return source
    anchor = "        if e.get('tier')=='blocked': errors.append('screening_blocked')\n"
    if source.count(anchor) != 1:
        raise ValueError('unified guard insertion anchor not found exactly once')
    return source.replace(anchor, ZEC_GUARD + anchor, 1)

def apply(root, write=False):
    root = Path(root)
    updated = {}
    for filename, marker in TARGETS.items():
        path = root / filename
        original = path.read_text(encoding='utf-8')
        updated[filename] = patch_tuple(original, marker)
    filename = 'unified_guard_v548.py'
    updated[filename] = patch_guard((root / filename).read_text(encoding='utf-8'))
    for filename, content in updated.items():
        compile(content, filename, 'exec')
    if write:
        for filename, content in updated.items():
            (root / filename).write_text(content, encoding='utf-8')
    return updated

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    result = apply(args.root, args.apply)
    print('ZEC patch:', 'APPLIED' if args.apply else 'VALIDATED_ONLY', ', '.join(result))
