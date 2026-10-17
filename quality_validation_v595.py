"""v5.9.5 research-only comparative volume, RR sanity and queue simulation.
Does not modify production scores, gates, queues or send notifications.
"""
import datetime as dt
import json
import math
from pathlib import Path
from historical_reliability_v594 import candle_history, relative_volume_at, numeric, reasons_view, replay_delivery
from dual_screen_v53 import COINS

THRESHOLDS=(1.0,1.1,1.2,1.3)

def volume_comparison(market):
    result={}
    for coin in COINS:
        frames=market.get('pairs',{}).get(coin+'USDT',{}).get('frames',{})
        data={}
        for tf,seconds in (('1h',3600),('4h',14400)):
            cs,error=candle_history(frames.get(tf,{}),seconds)
            if error:
                data[tf]={'status':'UNVERIFIED','reason':error}
                continue
            values=[relative_volume_at(cs,i) for i in range(20,len(cs))]
            data[tf]={'status':'AUDIT_ONLY','observations':len(values),
                      'counts':{str(t):sum(v is not None and v>=t for v in values) for t in THRESHOLDS},
                      'latest':round(values[-1],4) if values[-1] is not None else None}
        # 1h/4h samples are not independent aligned event observations; no joint pass rate.
        result[coin]=data
    return result

def rr_sanity(e,fee_bps=20,slippage_bps=20):
    reasons=[]
    price=e.get('reference_price_usdt');levels=e.get('static_levels') or {}
    support=levels.get('support');resistance=levels.get('resistance')
    if not all(numeric(v) and v>0 for v in (price,support,resistance)) or not support<price<resistance:
        return {'status':'BLOCK','reasons':['missing_or_invalid_entry_stop_target'],'gross_rr':None,'net_rr':None}
    risk=price-support;reward=resistance-price
    if risk/price<0.005:reasons.append('stop_distance_below_0_5_percent_sensitivity')
    if risk/price>0.15:reasons.append('stop_distance_above_15_percent_sensitivity')
    # Two-sided illustrative round-trip cost, NOT verified venue fee or actual slippage.
    cost=price*(fee_bps+slippage_bps)/10000
    net_risk=risk+cost
    net_reward=reward-cost
    net_rr=net_reward/net_risk if net_risk>0 else None
    if net_reward<=0:reasons.append('reward_not_positive_after_assumed_costs')
    if net_rr is None or net_rr<3:reasons.append('cost_adjusted_rr_below_3')
    return {'status':'REVIEW' if reasons else 'SENSITIVITY_PASS', 'reasons':reasons,
            'gross_rr':round(reward/risk,4),'net_rr':round(net_rr,4) if net_rr is not None else None,
            'stop_distance_percent':round(100*risk/price,4),
            'assumed_round_trip_cost_bps':fee_bps+slippage_bps,
            'assumption_only':True}

def replay_scenarios():
    good={'id':'synthetic:confirmed:100','eligible':True,'confirmed':True}
    bad={'id':'synthetic:forming:101','eligible':True,'confirmed':False}
    first=replay_delivery([good,bad]); second=replay_delivery([good,bad],first['pending_ids'])
    recovery=replay_delivery([good],first['pending_ids'])
    checks={'one_valid_queued':sum(x['status']=='DRY_RUN_QUEUED' for x in first['results'])==1,
            'forming_blocked':any(x['status']=='BLOCK' for x in first['results']),
            'replay_duplicate_suppressed':any(x['status']=='DUPLICATE_SUPPRESSED' for x in second['results']),
            'pending_preserved':first['pending_ids']==second['pending_ids']==recovery['pending_ids'],
            'no_network_or_delivery':all(x['sent']==0 and x['acknowledged']==0 for x in (first,second,recovery))}
    return {'checks':checks,'status':'PASS_SIMULATION_ONLY' if all(checks.values()) else 'BLOCK',
            'limitations':['In-memory replay only; no process restart, API outage or transport acknowledgement tested']}

def evaluate(market,dual,guard,now):
    stale=[]
    for name,doc in (('market',market),('dual',dual),('guard',guard)):
        try:age=now-dt.datetime.fromisoformat(doc['generated_at_utc'].replace('Z','+00:00')).timestamp()
        except (KeyError,TypeError,ValueError,AttributeError):age=float('inf')
        if not 0<=age<=5400:stale.append(name)
    if stale:return {'status':'BLOCK','reasons':['stale_'+x for x in stale], 'release_6_0_0_approved':False}
    evals={e.get('coin'):e for e in dual.get('evaluations',[]) if isinstance(e,dict)}
    rows={}
    for coin in COINS:
        e=evals.get(coin,{})
        gate=guard.get('coins',{}).get(coin,{}).get('positive_publication_gate')
        reasons=[]
        if not numeric(e.get('score')):reasons.append('missing_or_stale_market_data')
        if gate!='PASS':reasons.append('original_gate_not_passed')
        for tf in ('1h','4h'):
            v=e.get('relative_volume_'+tf)
            if not numeric(v) or v<1.3:reasons.append('volume_'+tf+'_below_candidate_threshold')
        rr=rr_sanity(e)
        if rr['status']!='SENSITIVITY_PASS':reasons.extend(rr['reasons'])
        rows[coin]={'status':'BLOCK' if reasons else 'CANDIDATE_SENSITIVITY_PASS',
                    'score':e.get('score'),'original_gate':gate,
                    **reasons_view(reasons,{'relative_volume_1h':e.get('relative_volume_1h'),
                                           'relative_volume_4h':e.get('relative_volume_4h')}),
                    'rr_sensitivity':rr}
    replay=replay_scenarios()
    return {'schema_version':'5.9.5','generated_at_utc':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),
            'status':'PASS_RESEARCH_ONLY' if replay['status']=='PASS_SIMULATION_ONLY' else 'BLOCK',
            'coins':rows,'volume_threshold_comparison':volume_comparison(market),
            'queue_replay':replay,'summary':{'coins_blocked':sum(x['status']=='BLOCK' for x in rows.values()),
                       'coins_evaluated':len(rows),'sent':0,'acknowledged':0,'live_scores_modified':0,
                       'publication_gates_modified':0},'release_6_0_0_approved':False,
            'limitations':['Volume threshold comparison is not a signal backtest or predictive win rate',
                           '1h and 4h counts are separate, not joint event-aligned probabilities',
                           'Fee/slippage and stop distance are sensitivity assumptions only',
                           'No walk-forward or historical trade entry/exit simulation',
                           'No real transport, process-restart recovery, or live multi-run uptime',
                           'No production score, gate, threshold, queue or order modification']}

def main():
    root=Path('data')
    load=lambda name:json.loads((root/name).read_text(encoding='utf-8'))
    r=evaluate(load('multisource_market.json'),load('dual_screen_v53.json'),
               load('unified_guard_v548.json'),dt.datetime.now(dt.timezone.utc).timestamp())
    (root/'quality_validation_v595.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(r,ensure_ascii=False,indent=2))
    if r['status']=='BLOCK':raise SystemExit(1)
if __name__=='__main__':main()
