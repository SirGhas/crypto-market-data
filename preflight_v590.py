"""v5.9.0 read-only gate divergence and delivery preflight. No sends or orders."""
import datetime as dt
import json
from pathlib import Path

TARGETS=('AAVE','AVAX','LINK','SUI')
ROOT=Path('data')

def fresh(doc, now, max_age=5400):
    try:
        t=dt.datetime.fromisoformat(doc['generated_at_utc'].replace('Z','+00:00')).timestamp()
        return 0 <= now-t <= max_age
    except (TypeError, ValueError, KeyError, AttributeError):
        return False

def evaluate(candidate, dual, guard, outbox, lifecycle, now):
    problems=[]; details={}
    for name, doc in [('candidate',candidate),('dual',dual),('guard',guard),('lifecycle',lifecycle)]:
        if not isinstance(doc,dict) or not fresh(doc,now): problems.append(name+':stale_or_invalid')
    if not isinstance(outbox,dict) or not isinstance(outbox.get('pending'),dict) or not isinstance(outbox.get('delivered_ids'),list):
        problems.append('outbox:invalid')
    if problems:
        return report(now,problems,details,0)
    evaluations={e.get('coin'):e for e in dual.get('evaluations',[]) if isinstance(e,dict)}
    divergences=0
    for coin in TARGETS:
        c=candidate.get('coins',{}).get(coin,{})
        d=evaluations.get(coin,{})
        g=guard.get('coins',{}).get(coin,{})
        old_gate=g.get('positive_publication_gate')
        hypot=c.get('hypothetical_guard')
        reasons=[]
        if not isinstance(d.get('score'),int) or isinstance(d.get('score'),bool): reasons.append('missing_score')
        if c.get('old_score')!=d.get('score'): reasons.append('score_mismatch')
        if c.get('old_gate')!=old_gate: reasons.append('original_gate_mismatch')
        if old_gate not in ('PASS','BLOCK'): reasons.append('invalid_original_gate')
        if c.get('effective_publication')!='BLOCK': reasons.append('unsafe_effective_publication')
        if c.get('status') not in ('CANDIDATE_READY','BLOCK'): reasons.append('unknown_candidate_status')
        if c.get('candidate_score') is not None and isinstance(d.get('score'),int):
            delta=c['candidate_score']-d['score']
            if delta not in (-5,0,5): reasons.append('invalid_delta')
        else: delta=None
        divergent=hypot in ('PASS','BLOCK') and old_gate in ('PASS','BLOCK') and hypot!=old_gate
        if divergent: divergences+=1
        if divergent and c.get('status')!='BLOCK': reasons.append('unblocked_gate_divergence')
        if reasons: problems.extend(coin+':'+r for r in reasons)
        details[coin]={'old_score':d.get('score'),'candidate_score':c.get('candidate_score'),
            'delta':delta,'original_tier':d.get('tier'),'candidate_status':c.get('status'),
            'original_gate':old_gate,'hypothetical_gate':hypot,'gate_divergence':divergent,
            'effective_publication':'BLOCK','validated_rr':d.get('risk_reward_validated_levels'),
            'static_levels':d.get('static_levels'), 'volume_1h':d.get('relative_volume_1h'),
            'volume_4h':d.get('relative_volume_4h'), 'hypothetical_guard_reasons':c.get('hypothetical_guard_reasons'),
            'diagnostic_reasons':reasons}
    pending=outbox['pending']; delivered=set(outbox['delivered_ids'])
    if any(eid in delivered for eid in pending): problems.append('outbox:pending_already_delivered')
    if any(not isinstance(eid,str) or not eid for eid in pending): problems.append('outbox:invalid_event_id')
    if any(not isinstance(item,dict) or item.get('status')!='PENDING_DELIVERY' or not isinstance(item.get('event'),dict) or item['event'].get('id')!=eid for eid,item in pending.items()):
        problems.append('outbox:invalid_pending_record')
    # This is a dry-run readiness check, not a delivery acknowledgement.
    return report(now,problems,details,divergences,pending_count=len(pending))

def report(now,problems,details,divergences,pending_count=0):
    return {'schema_version':'5.9.0','generated_at_utc':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),
      'status':'BLOCK' if problems else ('REVIEW_REQUIRED' if divergences else 'PASS_DRY_RUN'),
      'reasons':problems,'gate_divergences':divergences,'coins':details,
      'delivery':{'pending':pending_count,'transport_configured':False,'sent':0,'acknowledged':0,
                  'delivery_tested_end_to_end':False},'release_6_0_0_approved':False,
      'limitations':['No live transport test','No independent price attestation','No production score mutation',
                     'No orders or actual notifications','Gate divergences require explicit review']}

def main():
    def load(name): return json.loads((ROOT/name).read_text(encoding='utf-8'))
    now=dt.datetime.now(dt.timezone.utc).timestamp()
    output=evaluate(load('controlled_candidate_v580.json'),load('dual_screen_v53.json'),
      load('unified_guard_v548.json'),load('delivery_outbox_state_v550.json'),
      load('event_lifecycle_v549.json'),now)
    ROOT.mkdir(exist_ok=True)
    (ROOT/'preflight_v590.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':output['status'],'reasons':output['reasons'],
        'gate_divergences':output['gate_divergences'],'coins':output['coins'],
        'delivery':output['delivery'],'release_6_0_0_approved':False},indent=2))
    if output['status']=='BLOCK': raise SystemExit(1)

if __name__=='__main__':main()
