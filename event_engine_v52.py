"""Event-only 4H structure watcher. Research signals, never order instructions."""
import datetime as dt
import json
from pathlib import Path

ROOT = Path('data')
SYMBOLS = ('BTC','ETH','BNB','SOL','LTC','LINK','XRP','AVAX','SUI','AAVE')
MIN_VOLUME = 1.3
NEAR_LEVEL_PCT = 1.5

def read(path, fallback):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError): return fallback

def scan(coin, pairs, now):
    frames = pairs.get(coin+'USDT',{}).get('frames',{})
    if any(frames.get(k,{}).get('status')!='available' for k in ('4h','1h','15m')):
        return {'coin':coin,'status':'blocked','reason':'missing_required_closed_candles'},[]
    four,one,fifteen = [frames[k]['candles'] for k in ('4h','1h','15m')]
    if min(len(four),len(one),len(fifteen))<233:
        return {'coin':coin,'status':'blocked','reason':'insufficient_candles'},[]
    end4=four[-1]['t']+14400
    end1=one[-1]['t']+3600
    end15=fifteen[-1]['t']+900
    if any(x>now+120 for x in (end4,end1,end15)) or now-end4>14400+300 or now-end1>3900 or now-end15>1200:
        return {'coin':coin,'status':'blocked','reason':'stale_or_future_candle'},[]
    last=four[-1]; previous=four[-21:-1]
    high=max(x['h'] for x in previous); low=min(x['l'] for x in previous)
    avg4=sum(x['v'] for x in previous)/20
    volume4=last['v']/avg4 if avg4>0 else None
    avg1=sum(x['v'] for x in one[-21:-1])/20
    volume1=one[-1]['v']/avg1 if avg1>0 else None
    sma4=sum(x['c'] for x in four[-233:])/233
    sma1=sum(x['c'] for x in one[-233:])/233
    sma15=sum(x['c'] for x in fifteen[-233:])/233
    price=one[-1]['c']
    cross= pairs.get(coin+'BTC',{}).get('frames',{}).get('4h',{}) if coin!='BTC' else None
    rel=None
    if cross and cross.get('status')=='available' and len(cross.get('candles',[]))>=233:
        cs=cross['candles']; crossend=cs[-1]['t']+14400
        if 0<=now-crossend<=14700:
            rel=cs[-1]['c']>sum(x['c'] for x in cs[-233:])/233
    # Only prior completed 4H candles define levels. Never use a live forming candle.
    closebreak=last['c']>high and last['o']<=high
    closedown=last['c']<low and last['o']>=low
    reclaim=last['l']<low and last['c']>low
    rejection=last['h']>high and last['c']<high
    nearres=abs(price/high-1)*100<=NEAR_LEVEL_PCT
    nearsup=abs(price/low-1)*100<=NEAR_LEVEL_PCT
    # These are observations, not buy approvals. Volume is required for stronger status.
    candidates=[]
    for typ,level,condition in (
        ('4h_closed_breakout',high,closebreak),('4h_closed_breakdown',low,closedown),
        ('4h_support_reclaim',low,reclaim),('4h_resistance_rejection',high,rejection),
        ('approaching_resistance',high,nearres),('approaching_support',low,nearsup)):
        if not condition: continue
        confirmed_volume=volume4 is not None and volume4>=MIN_VOLUME
        early=typ.startswith('approaching_') or not confirmed_volume
        event={'id':f'{coin}:{typ}:{last["t"]}', 'coin':coin,'event_type':typ,
               'status':'forming_watch' if early else 'technical_event_needs_context',
               'level_usdt':round(level,9),'reference_price_usdt':price,
               'reference_price_kind':'last_closed_1h_not_live',
               'distance_from_level_percent':round((price/level-1)*100,3),
               'volume_ratio_4h':round(volume4,3) if volume4 is not None else None,
               'volume_ratio_1h':round(volume1,3) if volume1 is not None else None,
               'volume_confirmed_4h':confirmed_volume,
               'trend_4h_above_sma233':last['c']>sma4,
               'lower_tf_confirmed':one[-1]['c']>sma1 and fifteen[-1]['c']>sma15,
               'relative_strength_vs_btc':rel,
               'source_4h':frames['4h']['source'],'source_1h':frames['1h']['source'],
               'closed_4h_at_utc':dt.datetime.fromtimestamp(end4,dt.timezone.utc).isoformat(),
               'reason_not_buy_signal':'Requires BTC structure, dominance trend, validated levels and risk/reward; cross may be missing'}
        candidates.append(event)
    return {'coin':coin,'status':'scanned','4h_support':low,'4h_resistance':high,
            'relative_strength_vs_btc':rel,'4h_volume_ratio':round(volume4,3) if volume4 is not None else None,
            'observations':len(candidates)},candidates

def main():
    market=read(ROOT/'multisource_market.json',None)
    if not market: raise RuntimeError('multisource_market.json missing')
    now=dt.datetime.now(dt.timezone.utc)
    source=dt.datetime.fromisoformat(market['generated_at_utc'].replace('Z','+00:00'))
    if not 0<=(now-source).total_seconds()<5400: raise RuntimeError('Source data stale')
    state=read(ROOT/'event_state_v52.json',{'seen_ids':[]})
    seen=set(state.get('seen_ids',[]))
    results=[]; events=[]
    for coin in SYMBOLS:
        result,items=scan(coin,market['pairs'],now.timestamp())
        results.append(result);events.extend(items)
    fresh=[x for x in events if x['id'] not in seen]
    # De-duplicate only observations, not repeated news or alerts from other systems.
    seen.update(x['id'] for x in fresh)
    out={'schema_version':52,'generated_at_utc':now.isoformat(),
         'source_generated_at_utc':market['generated_at_utc'],
         'mode':'event_screening_only_no_push_no_orders',
         'observations':results,'new_events':fresh,
         'summary':{'scanned':sum(x['status']=='scanned' for x in results),
                    'blocked':sum(x['status']=='blocked' for x in results),
                    'new_events':len(fresh),
                    'forming':sum(x['status']=='forming_watch' for x in fresh)},
         'limitations':['Levels are prior 20 4h high/low, not multi-touch validated',
                        'Not a TradingView or Binance feed',
                        'No automatic notification is connected',
                        'Missing BTC crosses must not be treated as strength confirmation']}
    ROOT.mkdir(exist_ok=True)
    (ROOT/'events_v52.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'event_state_v52.json').write_text(json.dumps({'seen_ids':sorted(seen)[-3000:]},indent=2),encoding='utf-8')
    print(json.dumps(out['summary']))
if __name__=='__main__': main()
