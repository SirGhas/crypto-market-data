"""v5.8.0 controlled candidate: fail-closed, read-only, no live score/guard mutation."""
import copy
import datetime as dt
import json
import math
from pathlib import Path

from shadow_relative_screen_v553 import evaluate as shadow_evaluate
from unified_guard_v548 import evaluate as guard_evaluate
from relative_strength_audit_v552 import age_ok

ROOT = Path('data')
TARGETS = ('AAVE','AVAX','LINK','SUI')


def inspect(derived, dual, market, guard, liquidity, parity, lifecycle, outbox, now):
    inputs = (derived, dual, market, guard, liquidity, parity, lifecycle)
    if not all(isinstance(x,dict) and age_ok(x,now) for x in inputs):
        raise ValueError('stale_or_missing_input')
    if not isinstance(outbox,dict) or not isinstance(outbox.get('pending'),dict) or not isinstance(outbox.get('delivered_ids'),list):
        raise ValueError('invalid_outbox')
    original_bytes = json.dumps((inputs,outbox),sort_keys=True)
    shadow = shadow_evaluate(derived,dual,market,guard,now)
    original = {e.get('coin'):e for e in dual.get('evaluations',[]) if isinstance(e,dict)}
    candidate_dual = copy.deepcopy(dual)
    results = {}
    for coin in TARGETS:
        s = shadow['coins'].get(coin,{})
        reasons=[]
        if s.get('status')!='SHADOW_READY': reasons.append('shadow_not_ready')
        live_gate = guard.get('coins',{}).get(coin,{})
        if live_gate.get('positive_publication_gate') not in ('PASS','BLOCK'):
            reasons.append('missing_original_gate')
        if coin not in original or not isinstance(original[coin].get('score'),int):
            reasons.append('missing_original_score')
        if not reasons:
            old=original[coin]
            if s.get('original_score')!=old['score'] or s.get('original_tier')!=old.get('tier'):
                reasons.append('original_score_mismatch')
            if s.get('delta') not in (-5,0,5) or s.get('shadow_relative_points') not in (0,5):
                reasons.append('invalid_shadow_component')
            if s.get('shadow_score')!=old['score']+s['delta']:
                reasons.append('shadow_score_mismatch')
            if old.get('weights',{}).get('relative_btc')!=5:
                reasons.append('weight_changed')
        if not reasons:
            item=next(e for e in candidate_dual['evaluations'] if e['coin']==coin)
            item['score_components']['relative_btc']=s['shadow_relative_points']
            item['score']=s['shadow_score']
            item['tier']=s['shadow_tier']
            item['relative_strength_btc']=bool(s['shadow_relative_points'])
        results[coin]={'status':'CANDIDATE_READY' if not reasons else 'BLOCK',
                       'reason_codes':reasons,
                       'old_score':original.get(coin,{}).get('score'),
                       'candidate_score':s.get('shadow_score') if not reasons else None,
                       'old_gate':live_gate.get('positive_publication_gate'),
                       'effective_publication':'BLOCK'}
    # Evaluate hypothetical guard using the exact production gate function.
    candidate_guard=guard_evaluate(market,candidate_dual,liquidity,parity,now)
    for coin in TARGETS:
        entry=results[coin]
        hypothetical=candidate_guard['coins'].get(coin,{})
        old=guard['coins'].get(coin,{})
        if entry['status']=='CANDIDATE_READY':
            if old.get('score')!=entry['old_score'] or old.get('original_tier')!=original[coin].get('tier'):
                entry['reason_codes'].append('live_guard_score_or_tier_mismatch')
            if old.get('positive_publication_gate')!=hypothetical.get('positive_publication_gate'):
                entry['reason_codes'].append('publication_gate_divergence_manual_review')
            entry['hypothetical_guard']=hypothetical.get('positive_publication_gate')
            entry['hypothetical_guard_reasons']=hypothetical.get('reason_codes',[])
            if entry['reason_codes']:entry['status']='BLOCK'
            # No auto-promotion, even when both old and candidate gates PASS.
            entry['effective_publication']='BLOCK'
    # Never inspect pending as a permission to send: transport not implemented.
    if original_bytes!=json.dumps((inputs,outbox),sort_keys=True):
        raise AssertionError('input_mutation')
    return {'schema_version':'5.8.0',
            'generated_at_utc':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),
            'mode':'candidate_shadow_only_no_score_commit_no_push_no_orders',
            'coins':results,
            'outbox_observation':{'pending_count':len(outbox['pending']),
                                  'delivered_count':len(outbox['delivered_ids']),
                                  'transport_enabled':False},
            'summary':{'CANDIDATE_READY':sum(v['status']=='CANDIDATE_READY' for v in results.values()),
                       'BLOCK':sum(v['status']=='BLOCK' for v in results.values()),
                       'gate_divergences':sum('publication_gate_divergence_manual_review' in v['reason_codes'] for v in results.values()),
                       'live_scores_modified':0,'publication_gates_modified':0,
                       'new_notifications_sent':0,'direct_feeds_upgraded':0},
            'release_6_0_0_approved':False,
            'limitations':['Candidate scores are not live scores',
                           'No notification transport; no delivery acknowledgment',
                           'Guard PASS is not an event or buy signal',
                           'Gate divergence blocks candidate pending manual review']}


def main():
    def load(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
    now=dt.datetime.now(dt.timezone.utc).timestamp()
    result=inspect(load('derived_relative_strength_v551.json'),load('dual_screen_v53.json'),
                   load('multisource_market.json'),load('unified_guard_v548.json'),
                   load('liquidity_guard_v546.json'),load('price_parity_guard_v547.json'),
                   load('event_lifecycle_v549.json'),load('delivery_outbox_state_v550.json'),now)
    (ROOT/'controlled_candidate_v580.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'summary':result['summary'],'coins':result['coins'],
                      'outbox':result['outbox_observation'],'release_6_0_0_approved':False},indent=2))
    if result['summary']['BLOCK']:
        raise SystemExit('Candidate requires review; no production changes')

if __name__=='__main__':main()
