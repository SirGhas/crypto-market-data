"""v5.4.9: event lifecycle after all guards, idempotent publication queue.
No push, no orders. Does not modify scores, collectors or previous event state.
"""
import datetime as dt
import json
from pathlib import Path
from event_engine_v52 import SYMBOLS, scan

ROOT = Path('data')
POSITIVE = {'4h_closed_breakout', '4h_support_reclaim', 'approaching_resistance', 'approaching_support'}
STATE = ROOT / 'event_lifecycle_state_v549.json'
OUT = ROOT / 'event_lifecycle_v549.json'
MAX_IDS = 3000


def read(path, default=None):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        if default is not None:
            return default
        raise


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def age_ok(document, now, max_age=5400):
    try:
        stamp = dt.datetime.fromisoformat(document['generated_at_utc'].replace('Z', '+00:00')).timestamp()
        return 0 <= now - stamp <= max_age
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def reconcile(observations, audit, prior):
    """Re-evaluate suppressed candidates each run; dedup only after eligibility.

    IDs include the 4H candle start, so a later *different* 4H candle is a new
    event. A previously suppressed event can publish once if its guard later passes.
    """
    emitted = list(dict.fromkeys(prior.get('emitted_ids', [])))[-MAX_IDS:]
    emitted_set = set(emitted)
    eligible = []
    pending = []
    for event in observations:
        eid = event.get('id')
        coin = event.get('coin')
        if not isinstance(eid, str) or not eid or not isinstance(coin, str):
            continue
        if eid in emitted_set:
            continue
        gate = audit.get('coins', {}).get(coin, {}).get('positive_publication_gate')
        if event.get('event_type') in POSITIVE and gate != 'PASS':
            pending.append({'id': eid, 'coin': coin, 'event_type': event.get('event_type'),
                            'reason': 'positive_publication_gate_not_passed'})
            continue
        eligible.append(event)
        emitted_set.add(eid)
        emitted.append(eid)
    return {'emitted_ids': emitted[-MAX_IDS:]}, eligible, pending


def run(market, audit, prior, now):
    if not age_ok(market, now) or not age_ok(audit, now):
        raise RuntimeError('Stale market or unified guard; refusing event publication')
    observations = []
    blocked_scans = 0
    for coin in SYMBOLS:
        result, events = scan(coin, market.get('pairs', {}), now)
        blocked_scans += result.get('status') == 'blocked'
        observations.extend(events)
    new_state, eligible, pending = reconcile(observations, audit, prior)
    out = {'schema_version': '5.4.9',
           'generated_at_utc': dt.datetime.fromtimestamp(now, dt.timezone.utc).isoformat(),
           'mode': 'event_only_research_queue_no_push_no_orders',
           'new_publishable_events': eligible,
           'pending_unconfirmed': pending,
           'summary': {'scanned_coins': len(SYMBOLS), 'blocked_scans': blocked_scans,
                       'new_publishable_events': len(eligible), 'pending_unconfirmed': len(pending)},
           'limitations': ['No external notification transport configured',
                           'No live intrabar coverage',
                           'Emission means queued in JSON, not delivered to a device']}
    return new_state, out


def main():
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    market = read(ROOT / 'multisource_market.json')
    audit = read(ROOT / 'unified_guard_v548.json')
    prior = read(STATE, {'emitted_ids': []})
    state, output = run(market, audit, prior, now)
    # Write output first, then dedup state. GitHub workflow commits both atomically.
    save(OUT, output)
    save(STATE, state)
    print(json.dumps(output['summary']))


if __name__ == '__main__':
    main()
