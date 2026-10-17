"""v5.6.0 research-only integration audit. No mutation of production outputs."""
import datetime as dt
import json
from pathlib import Path
from shadow_relative_screen_v553 import evaluate as shadow_evaluate, tier

ROOT = Path('data')
COINS = ('AAVE','AVAX','LINK','SUI')
THRESHOLDS = (60,70,80)

def inspect(derived, dual, market, guard, now):
    before = json.dumps((derived,dual,market,guard),sort_keys=True)
    shadow = shadow_evaluate(derived,dual,market,guard,now)
    results={}
    for coin in COINS:
        item=shadow['coins'][coin]
        checks=[]
        if item['status']!='SHADOW_READY':
            checks.append('shadow_not_ready')
        else:
            original=next((e for e in dual['evaluations'] if e['coin']==coin),{})
            comp=original.get('score_components',{})
            if item['delta'] not in (-5,0,5):checks.append('unexpected_delta')
            if item['shadow_score']!=sum(comp.values())+item['delta']:checks.append('score_sum_mismatch')
            if item['shadow_relative_points'] not in (0,5):checks.append('invalid_relative_component')
            if item['shadow_publication_gate']!='NOT_EVALUATED_NEVER_AUTHORIZE':checks.append('shadow_gate_not_isolated')
            if guard['coins'][coin]['positive_publication_gate']!=item['original_publication_gate']:
                checks.append('original_gate_mismatch')
            if item['shadow_tier']!=tier(item['shadow_score'],dict(comp,relative_btc=item['shadow_relative_points']),original.get('risk_reward_validated_levels')):
                checks.append('tier_recalculation_mismatch')
        results[coin]={'status':'PASS' if not checks else 'BLOCK','reason_codes':checks,
                       'delta':item.get('delta'), 'original_tier':item.get('original_tier'),
                       'shadow_tier':item.get('shadow_tier'),
                       'original_publication_gate':item.get('original_publication_gate'),
                       'threshold_crossings':{str(t): bool(item.get('original_score',-1)<t<=item.get('shadow_score',-1)) for t in THRESHOLDS}}
    unchanged=before==json.dumps((derived,dual,market,guard),sort_keys=True)
    if not unchanged:raise AssertionError('production_input_mutated')
    return {'schema_version':'5.6.0','generated_at_utc':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),
            'mode':'shadow_integration_only_no_live_scoring_no_publication_no_orders',
            'coins':results,'summary':{'PASS':sum(v['status']=='PASS' for v in results.values()),
                'BLOCK':sum(v['status']=='BLOCK' for v in results.values()),
                'threshold_crossings':sum(sum(v['threshold_crossings'].values()) for v in results.values()),
                'live_scores_modified':0,'publication_gates_modified':0,'direct_feeds_upgraded':0},
            'limitations':['Threshold crossings are observations, not publication eligibility',
                           'No exchange BTC market or liquidity is verified by derived ratios',
                           'This workflow does not connect shadow results to production scoring or alerts']}

def main():
    def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
    now=dt.datetime.now(dt.timezone.utc).timestamp()
    report=inspect(read('derived_relative_strength_v551.json'),read('dual_screen_v53.json'),
                   read('multisource_market.json'),read('unified_guard_v548.json'),now)
    (ROOT/'integration_validation_v560.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(report['summary'],indent=2))
    print(json.dumps(report['coins'],indent=2))
    if report['summary']['BLOCK']:raise SystemExit('Integration blocked; no production change')
if __name__=='__main__':main()
