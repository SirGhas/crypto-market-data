"""v5.5.0: candle cadence audit and durable pending notification outbox.
Research only. Does not send notifications, alter scores, or mark deliveries successful.
"""
import datetime as dt
import json
from pathlib import Path

ROOT = Path('data')
INTERVALS = {'5m': 300, '15m': 900, '1h': 3600, '4h': 14400}
MAX_PENDING = 3000


def load(path, default=None):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        if default is not None:
            return default
        raise


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def timestamp(doc):
    return dt.datetime.fromisoformat(doc['generated_at_utc'].replace('Z', '+00:00')).timestamp()


def inspect_freshness(report, now):
    """UNCHANGED is normal only if the candle is still within its permitted age."""
    result = {'PASS': [], 'UNCHANGED_EXPECTED': [], 'STALE': [], 'UNVERIFIED': []}
    for key, item in report.get('feeds', {}).items():
        try:
            tf = key.rsplit(':', 1)[1]
            interval = INTERVALS[tf]
            status = item['status']
            age = float(item['age_seconds'])
            if status == 'UNVERIFIED':
                result['UNVERIFIED'].append(key)
            elif status == 'STALE' or age < 0 or age > interval + 300:
                result['STALE'].append(key)
            elif status == 'UNCHANGED':
                if item.get('candle_id_changed') is False and item.get('last_candle_id'):
                    result['UNCHANGED_EXPECTED'].append(key)
                else:
                    result['UNVERIFIED'].append(key)
            elif status == 'PASS':
                result['PASS'].append(key)
            else:
                result['UNVERIFIED'].append(key)
        except (KeyError, TypeError, ValueError, AttributeError):
            result['UNVERIFIED'].append(key)
    return result


def reconcile_outbox(lifecycle, prior):
    """Persist pending events across runs. Delivery is NEVER inferred from queueing."""
    pending = dict(prior.get('pending', {}))
    delivered = set(prior.get('delivered_ids', []))
    for event in lifecycle.get('new_publishable_events', []):
        eid = event.get('id')
        if isinstance(eid, str) and eid and eid not in delivered and eid not in pending:
            pending[eid] = {'event': event, 'status': 'PENDING_DELIVERY'}
    # Keep all existing pending; do not silently evict unsent events.
    if len(pending) > MAX_PENDING:
        raise RuntimeError('Outbox capacity reached; refusing to discard undelivered events')
    return {'schema_version': '5.5.0', 'pending': pending,
            'delivered_ids': list(prior.get('delivered_ids', []))}, list(pending.values())


def build(report, lifecycle, prior, now):
    if not (0 <= now - timestamp(report) <= 5400 and
            0 <= now - timestamp(lifecycle) <= 5400):
        raise RuntimeError('Stale audit or lifecycle input; refusing outbox update')
    health = inspect_freshness(report, now)
    state, pending = reconcile_outbox(lifecycle, prior)
    audit = {'schema_version': '5.5.0',
             'generated_at_utc': dt.datetime.fromtimestamp(now, dt.timezone.utc).isoformat(),
             'mode': 'research_only_no_transport_no_orders',
             'freshness': {'summary': {k: len(v) for k, v in health.items()},
                           'unchanged_expected_feeds': health['UNCHANGED_EXPECTED'],
                           'stale_feeds': health['STALE'],
                           'unverified_feeds': health['UNVERIFIED']},
             'outbox': {'pending_delivery': len(pending), 'new_events_in_lifecycle': len(lifecycle.get('new_publishable_events', [])),
                        'delivered_in_this_run': 0},
             'limitations': ['UNCHANGED is validated by age and candle ID, not independent exchange attestation',
                             'UNVERIFIED feeds remain unverified',
                             'No notification transport configured; no delivered status is assigned']}
    return state, audit


def main():
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    report = load(ROOT / 'freshness_report_v54.json')
    lifecycle = load(ROOT / 'event_lifecycle_v549.json')
    prior = load(ROOT / 'delivery_outbox_state_v550.json', {'pending': {}, 'delivered_ids': []})
    state, audit = build(report, lifecycle, prior, now)
    save(ROOT / 'delivery_outbox_state_v550.json', state)
    save(ROOT / 'delivery_health_v550.json', audit)
    print(json.dumps({'freshness': audit['freshness']['summary'], 'outbox': audit['outbox']}))


if __name__ == '__main__':
    main()
