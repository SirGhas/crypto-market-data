"""v5.9.1-v5.9.3 fail-closed shadow validation. No notifications/orders/state writes."""
import datetime as dt
import json
import math
from pathlib import Path

ROOT = Path('data')
TARGETS = ('AAVE', 'AVAX', 'LINK', 'SUI')
POSITIVE = {'4h_closed_breakout', '4h_support_reclaim'}
NEGATIVE = {'4h_closed_breakdown', '4h_resistance_rejection'}


def fresh(doc, now, max_age=5400):
    try:
        stamp = dt.datetime.fromisoformat(doc['generated_at_utc'].replace('Z', '+00:00')).timestamp()
        return isinstance(doc, dict) and 0 <= now-stamp <= max_age
    except (TypeError, KeyError, ValueError, AttributeError):
        return False


def positive_checks(e, event=None):
    """Extra conservative gate; never promotes a blocked production candidate."""
    reasons = []
    if not isinstance(e, dict):
        return ['missing_evaluation']
    def number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    for tf, key in [('1h', 'relative_volume_1h'), ('4h', 'relative_volume_4h')]:
        v = e.get(key)
        if not number(v) or v < 1.3:
            reasons.append(tf + '_volume_not_confirmed')
    rr = e.get('risk_reward_validated_levels')
    if not number(rr) or rr < 3:
        reasons.append('rr_below_3_or_unverified')
    levels = e.get('static_levels') or {}
    if not isinstance(levels, dict) or not all(number(levels.get(k)) and levels[k] > 0 for k in ('support','resistance')) or not (levels['support'] < levels['resistance']):
        reasons.append('validated_levels_missing')
    else:
        if levels.get('support_touches', 0) < 2 or levels.get('resistance_touches', 0) < 2:
            reasons.append('insufficient_level_touches')
    if event is not None:
        if event.get('event_type') not in POSITIVE:
            reasons.append('not_confirmed_positive_event_type')
        if event.get('status') != 'technical_event_needs_context':
            reasons.append('forming_or_unconfirmed_event')
        if event.get('volume_confirmed_4h') is not True:
            reasons.append('event_volume_unconfirmed')
        if event.get('lower_tf_confirmed') is not True:
            reasons.append('lower_timeframe_unconfirmed')
        if not isinstance(event.get('closed_4h_at_utc'), str):
            reasons.append('missing_closed_4h_id')
    return reasons


def evaluate(dual, guard, lifecycle, outbox, now):
    docs = {'dual': dual, 'guard': guard, 'lifecycle': lifecycle}
    failures = [name + '_stale_or_invalid' for name, doc in docs.items() if not fresh(doc, now)]
    if failures:
        return {'status':'BLOCK', 'reasons':failures, 'release_6_0_0_approved':False}
    if not isinstance(outbox,dict) or not isinstance(outbox.get('pending'),dict) or not isinstance(outbox.get('delivered_ids'),list):
        return {'status':'BLOCK','reasons':['invalid_outbox'],'release_6_0_0_approved':False}
    original = {x.get('coin'):x for x in dual.get('evaluations',[]) if isinstance(x,dict)}
    coins = {}
    for coin in TARGETS:
        g = guard.get('coins',{}).get(coin,{})
        e = original.get(coin)
        reasons = positive_checks(e)
        if g.get('positive_publication_gate') != 'PASS':
            reasons.append('original_gate_not_passed')
        coins[coin] = {'status':'BLOCK' if reasons else 'ADDITIONAL_CHECKS_PASS', 'reasons':reasons,
                       'score':e.get('score') if e else None,
                       'original_gate':g.get('positive_publication_gate')}
    pending = outbox['pending']
    delivered = outbox['delivered_ids']
    problems = []
    if len(delivered) != len(set(delivered)) or any(not isinstance(x,str) or not x for x in delivered):
        problems.append('invalid_or_duplicate_delivered_ids')
    if set(pending).intersection(delivered):
        problems.append('pending_delivered_collision')
    for key, value in pending.items():
        if not isinstance(key,str) or not key or not isinstance(value,dict) or value.get('status')!='PENDING_DELIVERY' or not isinstance(value.get('event'),dict) or value['event'].get('id')!=key:
            problems.append('invalid_pending_record')
    observed = set()
    event_checks=[]
    for event in lifecycle.get('new_publishable_events',[]):
        if not isinstance(event,dict):
            problems.append('malformed_lifecycle_event');continue
        eid, coin, typ = event.get('id'),event.get('coin'),event.get('event_type')
        reasons=[]
        if not isinstance(eid,str) or not eid or eid in observed or eid in pending or eid in delivered:
            reasons.append('invalid_duplicate_or_already_queued_id')
        if isinstance(eid,str): observed.add(eid)
        if typ in POSITIVE or typ == 'approaching_resistance' or typ == 'approaching_support':
            reasons.extend(positive_checks(original.get(coin),event))
            if guard.get('coins',{}).get(coin,{}).get('positive_publication_gate')!='PASS':
                reasons.append('original_gate_not_passed')
        elif typ not in NEGATIVE:
            reasons.append('unknown_event_type')
        # Negative observations are not buying signals; no positive volume gate applied.
        event_checks.append({'id':eid,'coin':coin,'event_type':typ,
                             'shadow_eligible':not reasons,'reasons':reasons})
    return {'schema_version':'5.9.3','generated_at_utc':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),
            'status':'BLOCK' if problems else 'PASS_SHADOW_WITH_BLOCKS', 'reasons':problems,
            'coins':coins,'events':event_checks,
            'summary':{'coins_blocked':sum(x['status']=='BLOCK' for x in coins.values()),
                       'event_checks':len(event_checks),
                       'shadow_eligible_events':sum(x['shadow_eligible'] for x in event_checks),
                       'pending':len(pending),'sent':0,'acknowledged':0,
                       'live_scores_modified':0,'publication_gates_modified':0},
            'release_6_0_0_approved':False,
            'limitations':['Shadow audit only; no transport or order execution',
                           '1.3x volume is a conservative candidate gate, not backtested',
                           'Historical backtest and multi-run persistence not proven',
                           'Existing lifecycle output is read-only; no event is sent']}


def main():
    def load(n):return json.loads((ROOT/n).read_text(encoding='utf-8'))
    now=dt.datetime.now(dt.timezone.utc).timestamp()
    result=evaluate(load('dual_screen_v53.json'),load('unified_guard_v548.json'),
                    load('event_lifecycle_v549.json'),load('delivery_outbox_state_v550.json'),now)
    ROOT.mkdir(exist_ok=True)
    (ROOT/'safety_reliability_v593.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result['status']=='BLOCK':raise SystemExit(1)

if __name__=='__main__':main()
