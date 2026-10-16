"""Conservative hourly screening. No orders, no push notifications, stdlib only."""
import datetime as dt
import json
from pathlib import Path

ROOT = Path('data')
MARKET = ROOT / 'market.json'
HISTORY = ROOT / 'dominance_history.json'
STATE = ROOT / 'signal_state.json'
OUTPUT = ROOT / 'signals.json'
COINS = ('ETH','BNB','SOL','LTC','LINK','XRP','AVAX','SUI','AAVE')
MIN_RELATIVE_VOLUME = 1.3
MIN_RR = 2.5
MAX_AGE_SECONDS = 90 * 60


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError):
        return default


def valid_entry(entry, now, max_age):
    ind = entry.get('indicators', {})
    if not ind.get('valid') or not ind.get('fresh'):
        return False
    t = ind.get('last_candle_start_utc')
    return isinstance(t, (int, float)) and 0 <= now-t <= max_age


def dominance_status(market, history):
    d = market.get('dominance', {})
    latest = {name: d.get(name, {}).get('value_percent') for name in ('BTC.D','USDT.D')}
    snaps = history.get('snapshots', [])
    usable = [s for s in snaps if all(isinstance(s.get('percent',{}).get(k), (int,float)) for k in latest)]
    # At least 12 distinct hourly snapshots; not OHLCV and not a TradingView equivalent.
    unique = {s.get('captured_at_utc','')[:13]: s for s in usable}
    enough = len(unique) >= 12
    return {'latest_percent':latest, 'historical_samples':len(unique),
            'trend_ready':enough, 'kind':'coingecko_market_cap_snapshots_not_ohlcv'}


def evaluate(coin, market, now, dom):
    pairs = market['markets'].get(coin, {})
    usd = pairs.get(f'{coin}/USD', {})
    cross = pairs.get(f'{coin}/BTC', {})
    reasons = []
    required = [('USD 4h',usd.get('4h'),5*3600),('USD 1h',usd.get('1h'),2*3600),
                ('USD 15m',usd.get('15m'),3600),('BTC 4h',cross.get('4h'),5*3600)]
    for label, entry, age in required:
        if not entry or not valid_entry(entry, now, age):
            reasons.append('missing_or_stale_'+label.replace(' ','_'))
    if reasons:
        return {'coin':coin,'status':'blocked','reasons':reasons}
    h4 = usd['4h']['indicators']
    h1 = usd['1h']['indicators']
    m15 = usd['15m']['indicators']
    rel = cross['4h']['indicators']
    if h4['close'] <= h4['sma233']:
        reasons.append('4h_below_sma233')
    if rel['close'] <= rel['sma233']:
        reasons.append('relative_strength_below_sma233')
    if h1['close'] <= h1['prior20_high']:
        reasons.append('no_1h_breakout')
    if m15['close'] <= m15['sma233']:
        reasons.append('15m_not_confirmed')
    volume = h1.get('relative_volume20')
    if not h1.get('volume_confirmation_available') or volume is None or volume < MIN_RELATIVE_VOLUME:
        reasons.append('insufficient_real_usd_volume')
    entry = h1['close']
    stop = h1['prior20_low']
    risk = entry-stop
    # Mechanical 2.5R objective is a planning level, NOT verified market resistance.
    rr = MIN_RR if risk > 0 else 0
    if risk <= 0 or risk/entry > .08:
        reasons.append('invalid_or_wide_stop')
    if reasons:
        return {'coin':coin,'status':'rejected','reasons':reasons}
    candle = int(h1['last_candle_start_utc'])
    event_id = f'{coin}:1h_breakout:{candle}'
    result = {'coin':coin,'status':'watch','event_id':event_id,
              'entry_reference_usd':entry,'stop_reference_usd':stop,
              'illustrative_target_2_5R_usd':round(entry + MIN_RR*risk, 10),
              'illustrative_rr':rr,'volume_ratio_1h':volume,
              'candle_start_utc':candle,
              'notes':'Screening event only; target is not validated resistance; no execution authorization'}
    if not dom['trend_ready']:
        result['reasons']=['dominance_history_insufficient_for_trend_confirmation']
    return result


def main():
    market = read_json(MARKET, None)
    if not market:
        raise RuntimeError('Missing market.json; cannot screen')
    now = dt.datetime.now(dt.timezone.utc)
    stamp = dt.datetime.fromisoformat(market['generated_at_utc'].replace('Z','+00:00'))
    if not 0 <= (now-stamp).total_seconds() <= MAX_AGE_SECONDS:
        raise RuntimeError('Market snapshot stale; refusing to publish new signals')
    dom = dominance_status(market, read_json(HISTORY, {}))
    previous = read_json(STATE, {'seen_event_ids':[]})
    seen = set(previous.get('seen_event_ids', []))
    evaluated = [evaluate(c,market,now.timestamp(),dom) for c in COINS]
    new_events = [x for x in evaluated if x['status']=='watch' and x['event_id'] not in seen]
    for x in new_events:
        seen.add(x['event_id'])
    output = {'generated_at_utc':now.isoformat(), 'source_generated_at_utc':market['generated_at_utc'],
              'mode':'screening_only_no_trades_no_notifications', 'dominance':dom,
              'new_events':new_events, 'evaluations':evaluated,
              'summary':{'evaluated':len(evaluated),'new_events':len(new_events),
                         'blocked':sum(x['status']=='blocked' for x in evaluated),
                         'rejected':sum(x['status']=='rejected' for x in evaluated)}}
    ROOT.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    STATE.write_text(json.dumps({'seen_event_ids':sorted(seen)[-1000:]},indent=2),encoding='utf-8')
    print(json.dumps(output['summary']))

if __name__ == '__main__':
    main()
