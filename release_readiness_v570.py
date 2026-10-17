"""v5.7.0 fail-closed release readiness: read-only, never grants publication."""
import datetime as dt
import json
from pathlib import Path

ROOT = Path('data')
TARGETS = ('AAVE', 'AVAX', 'LINK', 'SUI')


def recent(doc, now, max_age=5400):
    try:
        stamp = dt.datetime.fromisoformat(doc['generated_at_utc'].replace('Z', '+00:00'))
        return stamp.tzinfo is not None and 0 <= now-stamp.timestamp() <= max_age
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def evaluate(integration, shadow, derived, market, guard, health, now):
    reasons = []
    for name, doc in [('integration',integration),('shadow',shadow),('derived',derived),('market',market),('guard',guard),('health',health)]:
        if not isinstance(doc, dict) or not recent(doc, now):
            reasons.append(name+':stale_or_missing_timestamp')
    if reasons:
        return result(reasons, {}, now)
    if integration.get('summary',{}).get('PASS') != 4 or integration.get('summary',{}).get('BLOCK') != 0:
        reasons.append('integration:not_all_pass')
    if shadow.get('summary',{}).get('SHADOW_READY') != 4 or shadow.get('summary',{}).get('SHADOW_BLOCKED') != 0:
        reasons.append('shadow:not_all_ready')
    for key in ('live_scores_modified','publication_gates_modified','direct_feeds_upgraded'):
        if integration.get('summary',{}).get(key) != 0:
            reasons.append('integration:unexpected_'+key)
    for key in ('live_scores_modified','publication_gates_modified','direct_feeds_upgraded'):
        if shadow.get('summary',{}).get(key) != 0:
            reasons.append('shadow:unexpected_'+key)
    freshness = health.get('freshness',{}).get('summary',{})
    if freshness.get('STALE',0) != 0:
        reasons.append('freshness:stale_feeds')
    if not isinstance(freshness.get('UNVERIFIED'),int):
        reasons.append('freshness:missing_unverified_count')
    details={}
    for coin in TARGETS:
        cross=coin+'BTC'
        a=integration.get('coins',{}).get(coin,{})
        s=shadow.get('coins',{}).get(coin,{})
        frames=derived.get('pairs',{}).get(cross,{}).get('frames',{})
        direct=market.get('pairs',{}).get(cross,{}).get('frames',{})
        g=guard.get('coins',{}).get(coin,{})
        flags=[]
        if a.get('status')!='PASS' or s.get('status')!='SHADOW_READY': flags.append('integration_or_shadow_not_ready')
        if any(frames.get(tf,{}).get('status')!='DERIVED_READY' or frames.get(tf,{}).get('publication_eligible') is not False or frames.get(tf,{}).get('direct_btc_market_verified') is not False for tf in ('5m','15m','1h','4h')):
            flags.append('derived_not_research_only_ready')
        if any(direct.get(tf,{}).get('status')=='available' for tf in ('5m','15m','1h','4h')):
            flags.append('direct_market_provenance_changed')
        if a.get('original_publication_gate')!=g.get('positive_publication_gate') or s.get('original_publication_gate')!=g.get('positive_publication_gate'):
            flags.append('guard_mismatch')
        if s.get('shadow_publication_gate')!='NOT_EVALUATED_NEVER_AUTHORIZE':
            flags.append('shadow_publication_authorization_detected')
        if flags: reasons.extend(cross+':'+f for f in flags)
        details[coin]={'status':'PASS' if not flags else 'BLOCK','reasons':flags,'hypothetical_delta':s.get('delta'), 'live_publication_gate':g.get('positive_publication_gate')}
    return result(reasons, details, now)


def result(reasons, details, now):
    return {'schema_version':'5.7.0','generated_at_utc':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),
            'mode':'read_only_preproduction_gate_no_orders_no_notifications',
            'status':'PASS_SHADOW_ONLY' if not reasons else 'BLOCK',
            'reasons':reasons,'coins':details,
            'release_6_0_0_approved':False,
            'next_gates':['production scoring integration with regression tests', 'verified end-to-end event and alert transport', 'operational freshness and failure recovery', 'manual release approval'],
            'limitations':['PASS_SHADOW_ONLY is not approval to change production scoring or publish alerts', 'Derived X/BTC has no direct traded liquidity or volume']}


def main():
    def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
    now=dt.datetime.now(dt.timezone.utc).timestamp()
    report=evaluate(read('integration_validation_v560.json'),read('shadow_relative_screen_v553.json'),
                    read('derived_relative_strength_v551.json'),read('multisource_market.json'),
                    read('unified_guard_v548.json'),read('delivery_health_v550.json'),now)
    ROOT.mkdir(exist_ok=True)
    (ROOT/'release_readiness_v570.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'reasons':report['reasons'],'coins':report['coins'],'release_6_0_0_approved':False},indent=2))
    if report['status']=='BLOCK':raise SystemExit(1)

if __name__=='__main__':main()
