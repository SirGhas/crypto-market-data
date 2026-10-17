"""v5.5.3 shadow screening: 5-point existing relative_btc slot, never publication."""
import datetime as dt
import json
from pathlib import Path
from relative_strength_audit_v552 import evaluate as audit_evaluate

ROOT = Path('data')

def tier(score, components, rr):
    if score >= 80 and components.get('static_levels', 0) >= 20 and components.get('volume', 0) >= 15 and rr is not None and rr >= 2:
        return 'tier_1_priority_watch'
    if score >= 70 and rr is not None and rr >= 2.5:
        return 'tier_2_conditional_watch'
    if score >= 60 and rr is not None and rr >= 3:
        return 'tier_2_conditional_watch'
    return 'below_threshold_watch_only'

def evaluate(derived, dual, market, guard, now):
    audit = audit_evaluate(derived, dual, market, now)
    # Existing guard is observational input only; never grant publication.
    from relative_strength_audit_v552 import age_ok
    if not age_ok(guard, now) or not isinstance(guard.get('coins'), dict):
        raise ValueError('stale_or_missing_original_publication_guard')
    originals = {e['coin']: e for e in dual.get('evaluations', []) if isinstance(e, dict) and isinstance(e.get('coin'), str)}
    results = {}
    for coin, a in audit['results'].items():
        old = originals.get(coin, {})
        entry = {'status': 'SHADOW_BLOCKED', 'reason_codes': list(a['reason_codes']),
                 'publication_gate_modified': False, 'live_score_modified': False}
        if a['status'] != 'AUDIT_READY':
            results[coin] = entry
            continue
        comp = old.get('score_components', {})
        old_score = old.get('score')
        rr = old.get('risk_reward_validated_levels')
        old_gate = guard['coins'].get(coin)
        if not isinstance(old_gate, dict) or old_gate.get('score') != old_score or old_gate.get('original_tier') != old.get('tier'):
            entry['reason_codes'].append('original_guard_mismatch')
        if not isinstance(comp, dict) or sum(v for v in comp.values() if isinstance(v, (int,float)) and not isinstance(v,bool)) != old_score:
            entry['reason_codes'].append('score_component_sum_mismatch')
        if old.get('weights', {}).get('relative_btc') != 5:
            entry['reason_codes'].append('relative_weight_not_five')
        if not isinstance(rr, (int,float)) and rr is not None:
            entry['reason_codes'].append('invalid_rr')
        if entry['reason_codes']:
            results[coin] = entry
            continue
        new_comp = dict(comp)
        new_comp['relative_btc'] = a['hypothetical_relative_points']
        shadow_score = old_score - comp['relative_btc'] + new_comp['relative_btc']
        shadow_tier = tier(shadow_score, new_comp, rr)
        entry.update(status='SHADOW_READY', original_score=old_score, shadow_score=shadow_score,
                     delta=shadow_score-old_score, original_tier=old['tier'], shadow_tier=shadow_tier,
                     original_publication_gate=old_gate.get('positive_publication_gate'),
                     shadow_publication_gate='NOT_EVALUATED_NEVER_AUTHORIZE',
                     shadow_qualified_by_score=shadow_tier in ('tier_1_priority_watch','tier_2_conditional_watch'),
                     original_relative_points=comp['relative_btc'], shadow_relative_points=new_comp['relative_btc'])
        results[coin] = entry
    return {'schema_version':'5.5.3','generated_at_utc':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),
            'mode':'shadow_only_no_live_score_or_guard_mutation_no_orders', 'coins':results,
            'summary':{'SHADOW_READY':sum(v['status']=='SHADOW_READY' for v in results.values()),
                       'SHADOW_BLOCKED':sum(v['status']=='SHADOW_BLOCKED' for v in results.values()),
                       'tier_changes':sum(v.get('shadow_tier') != v.get('original_tier') for v in results.values() if v['status']=='SHADOW_READY'),
                       'live_scores_modified':0,'publication_gates_modified':0,'direct_feeds_upgraded':0},
            'limitations':['Shadow scores are NOT used by unified_guard, lifecycle or delivery',
                           'Derived close ratios do NOT verify traded BTC market or liquidity',
                           'Tier changes in this report are hypothetical, not buy signals']}

def main():
    def read(name): return json.loads((ROOT/name).read_text(encoding='utf-8'))
    now=dt.datetime.now(dt.timezone.utc).timestamp()
    result=evaluate(read('derived_relative_strength_v551.json'),read('dual_screen_v53.json'),
                    read('multisource_market.json'),read('unified_guard_v548.json'),now)
    (ROOT/'shadow_relative_screen_v553.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'summary':result['summary'],'coins':{k:{x:v.get(x) for x in ('status','delta','original_tier','shadow_tier','original_publication_gate','reason_codes')} for k,v in result['coins'].items()}},indent=2))
if __name__=='__main__': main()
