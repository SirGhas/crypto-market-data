"""v5.4.8 unified publication eligibility and independent colour bands.
Runs after v5.4.6/v5.4.7. Never changes scores, weights, source candles, or orders.
Produces a separate event-only publication queue (no delivery connector).
"""
import datetime as dt
import json
from pathlib import Path

ROOT = Path('data')
POSITIVE = {'4h_closed_breakout','4h_support_reclaim','approaching_resistance','approaching_support'}
FRAMES = {'4h':14400,'1h':3600,'15m':900}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def band(score):
    if score is None: return 'blocked_gray'
    if score >= 80: return 'green_80_100'
    if score >= 70: return 'blue_70_79'
    if score >= 60: return 'yellow_60_69'
    return 'gray_below_60'


def fresh_market(market, coin, now):
    errors=[]
    for tf, seconds in FRAMES.items():
        f=market.get('pairs',{}).get(coin+'USDT',{}).get('frames',{}).get(tf,{})
        cs=f.get('candles',[])
        if f.get('status')!='available' or f.get('source')!='OKX Spot' or not isinstance(cs,list) or len(cs)<233:
            errors.append(tf+':missing_or_wrong_source');continue
        try:
            stamps=[int(c['t']) for c in cs[-233:]]
            if any(b-a!=seconds for a,b in zip(stamps,stamps[1:])):
                errors.append(tf+':noncontiguous')
            age=now-(stamps[-1]+seconds)
            if not 0<=age<=seconds+300: errors.append(tf+':stale_or_future')
        except (TypeError,ValueError,KeyError,OverflowError): errors.append(tf+':malformed')
    return errors


def evaluate(market, dual, liquidity, parity, now):
    result={'schema_version':'5.4.8','mode':'research_only_no_orders_no_push',
            'generated_at_utc':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),
            'coins':{},'bands':{'green_80_100':[],'blue_70_79':[],'yellow_60_69':[],
                                 'gray_below_60':[],'blocked_gray':[]},'eligible_positive_events':[],
            'limitations':['No verified BTC.D/USDT.D in scoring','No alert delivery configured',
                           'Scores are not probabilities or buy authorizations']}
    for e in dual.get('evaluations',[]):
        coin=e['coin'];score=e.get('score');colour=band(score)
        errors=fresh_market(market,coin,now)
        if coin in ('BNB','XRP') and parity.get('pairs',{}).get(coin,{}).get('status')!='PASS':
            errors.append('price_parity_unconfirmed')
        if coin=='XRP' and liquidity.get('status')!='PASS':
            errors.append('xrp_btc_liquidity_unconfirmed')
        if e.get('tier')=='blocked': errors.append('screening_blocked')
        if coin in ('BNB','XRP'):
            cross=market.get('pairs',{}).get(coin+'BTC',{}).get('frames',{}).get('4h',{})
            if cross.get('source')!='Gate.io Spot': errors.append('cross_source_not_gate')
        eligible=not errors and e.get('tier') in ('tier_1_priority_watch','tier_2_conditional_watch')
        entry={'score':score,'color_band':colour,'original_tier':e.get('tier'),
               'positive_publication_gate':'PASS' if eligible else 'BLOCK',
               'reason_codes':errors if errors else ([] if eligible else ['not_a_qualified_candidate']),
               'risk_reward':e.get('risk_reward_validated_levels')}
        result['coins'][coin]=entry
        result['bands'][colour].append(coin)
    return result


def publication_events(events, audit):
    """Do not re-emit duplicates; do not pretend publication is notification."""
    selected=[]
    for event in events.get('new_events',[]):
        coin=event.get('coin')
        if event.get('event_type') in POSITIVE:
            if audit['coins'].get(coin,{}).get('positive_publication_gate')!='PASS':
                continue
        selected.append(event)
    return selected


def main():
    market=read(ROOT/'multisource_market.json')
    dual=read(ROOT/'dual_screen_v53.json')
    events=read(ROOT/'events_v52.json')
    liquidity=read(ROOT/'liquidity_guard_v546.json')
    parity=read(ROOT/'price_parity_guard_v547.json')
    now=dt.datetime.now(dt.timezone.utc).timestamp()
    def age_ok(document):
        try:
            stamp=dt.datetime.fromisoformat(document['generated_at_utc'].replace('Z','+00:00')).timestamp()
            return 0<=now-stamp<=5400
        except (KeyError,TypeError,ValueError):return False
    if not all(age_ok(doc) for doc in (market,dual,events,liquidity,parity)):
        raise RuntimeError('Missing/stale guard input; refusing publication')
    audit=evaluate(market,dual,liquidity,parity,now)
    audit['eligible_positive_events']=publication_events(events,audit)
    audit['summary']={'green':len(audit['bands']['green_80_100']),
                      'blue':len(audit['bands']['blue_70_79']),
                      'yellow':len(audit['bands']['yellow_60_69']),
                      'publishable_new_events':len(audit['eligible_positive_events'])}
    write(ROOT/'unified_guard_v548.json',audit)
    print(json.dumps(audit['summary']))

if __name__=='__main__':main()
