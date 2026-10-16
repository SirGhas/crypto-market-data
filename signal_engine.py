"""Conservative hourly screening; no orders or notifications. Python 3.12 stdlib."""
import datetime as dt
import json
from pathlib import Path

ROOT = Path('data')
MARKET = ROOT / 'market.json'
HISTORY = ROOT / 'dominance_history.json'
STATE = ROOT / 'signal_state.json'
OUTPUT = ROOT / 'signals.json'
COINS = ('ETH', 'BNB', 'SOL', 'LTC', 'LINK', 'XRP', 'AVAX', 'SUI', 'AAVE')
FRAMES = {'5m': 300, '15m': 900, '1h': 3600, '4h': 14400}
MIN_RELATIVE_VOLUME = 1.3
MIN_RR = 2.5
MAX_SNAPSHOT_AGE = 90 * 60


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError):
        return default


def valid_entry(entry, now_ts, frame):
    """Validate a *closed* candle using its close time, not its start time.

    The last closed 4H candle may have started nearly eight hours ago.
    Permit one complete frame plus a 30-minute collection grace after close.
    """
    if not isinstance(entry, dict):
        return False
    ind = entry.get('indicators', {})
    if not ind.get('valid') or not ind.get('fresh'):
        return False
    start = ind.get('last_candle_start_utc')
    if not isinstance(start, (int, float)):
        return False
    frame_seconds = FRAMES[frame]
    close_ts = start + frame_seconds
    age_since_close = now_ts - close_ts
    return 0 <= age_since_close <= frame_seconds + 1800


def dominance_status(market, history):
    d = market.get('dominance', {})
    latest = {k: d.get(k, {}).get('value_percent') for k in ('BTC.D', 'USDT.D')}
    snaps = history.get('snapshots', [])
    usable = [s for s in snaps if all(isinstance(s.get('percent', {}).get(k), (int, float)) for k in latest)]
    unique = {s.get('captured_at_utc', '')[:13]: s for s in usable}
    return {
        'latest_percent': latest,
        'historical_samples': len(unique),
        'trend_ready': len(unique) >= 12,
        'kind': 'coingecko_market_cap_snapshots_not_ohlcv',
    }


def evaluate(coin, market, now_ts, dom):
    pairs = market.get('markets', {}).get(coin, {})
    usd = pairs.get(f'{coin}/USD', {})
    cross = pairs.get(f'{coin}/BTC', {})
    btc_usd = market.get('markets', {}).get('BTC', {}).get('BTC/USD', {})
    required = [
        ('USD_4h', usd.get('4h'), '4h'),
        ('USD_1h', usd.get('1h'), '1h'),
        ('USD_15m', usd.get('15m'), '15m'),
        ('BTC_cross_4h', cross.get('4h'), '4h'),
        ('BTC_market_4h', btc_usd.get('4h'), '4h'),
    ]
    missing = [f'missing_or_stale_{label}' for label, entry, frame in required
               if not valid_entry(entry, now_ts, frame)]
    if missing:
        return {'coin': coin, 'status': 'blocked', 'reasons': missing}

    h4 = usd['4h']['indicators']
    h1 = usd['1h']['indicators']
    m15 = usd['15m']['indicators']
    rel = cross['4h']['indicators']
    btc = btc_usd['4h']['indicators']
    reasons = []
    if btc['close'] <= btc['sma233']:
        reasons.append('btc_4h_below_sma233')
    if h4['close'] <= h4['sma233']:
        reasons.append('4h_below_sma233')
    if rel['close'] <= rel['sma233']:
        reasons.append('relative_strength_below_sma233')
    if h1['close'] <= h1['prior20_high']:
        reasons.append('no_closed_1h_breakout')
    if m15['close'] <= m15['sma233']:
        reasons.append('15m_not_confirmed')
    volume = h1.get('relative_volume20')
    if not h1.get('volume_confirmation_available') or volume is None or volume < MIN_RELATIVE_VOLUME:
        reasons.append('insufficient_real_usd_volume')
    entry = h1['close']
    stop = h1['prior20_low']
    risk = entry - stop
    if entry <= 0 or risk <= 0 or risk / entry > .08:
        reasons.append('invalid_or_wide_stop')
    if reasons:
        return {'coin': coin, 'status': 'rejected', 'reasons': reasons}

    # This is a screening candidate only. Dominance snapshots are not 4H candles.
    candle = int(h1['last_candle_start_utc'])
    event_id = f'{coin}:1h_breakout:{candle}'
    result = {
        'coin': coin, 'status': 'watch', 'event_id': event_id,
        'entry_reference_usd': entry, 'stop_reference_usd': stop,
        'illustrative_target_2_5R_usd': round(entry + MIN_RR * risk, 10),
        'illustrative_rr': MIN_RR, 'volume_ratio_1h': volume,
        'candle_start_utc': candle,
        'notes': 'Early watch only; 4H static breakout/retest and market target are NOT verified. No purchase recommendation.',
    }
    if not dom['trend_ready']:
        result['reasons'] = ['dominance_history_insufficient_for_trend_confirmation']
    return result


def main():
    market = read_json(MARKET, None)
    if not market:
        raise RuntimeError('Missing market.json; cannot screen')
    now = dt.datetime.now(dt.timezone.utc)
    stamp = dt.datetime.fromisoformat(market['generated_at_utc'].replace('Z', '+00:00'))
    if not 0 <= (now - stamp).total_seconds() <= MAX_SNAPSHOT_AGE:
        raise RuntimeError('Market snapshot stale; refusing to publish new signals')
    dom = dominance_status(market, read_json(HISTORY, {}))
    previous = read_json(STATE, {'seen_event_ids': []})
    seen = set(previous.get('seen_event_ids', []))
    evaluated = [evaluate(coin, market, now.timestamp(), dom) for coin in COINS]
    new_events = [e for e in evaluated if e['status'] == 'watch' and e['event_id'] not in seen]
    seen.update(e['event_id'] for e in new_events)
    output = {
        'generated_at_utc': now.isoformat(),
        'source_generated_at_utc': market['generated_at_utc'],
        'mode': 'screening_only_no_trades_no_notifications',
        'dominance': dom, 'new_events': new_events, 'evaluations': evaluated,
        'summary': {
            'evaluated': len(evaluated), 'new_events': len(new_events),
            'blocked': sum(e['status'] == 'blocked' for e in evaluated),
            'rejected': sum(e['status'] == 'rejected' for e in evaluated),
        },
    }
    ROOT.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    STATE.write_text(json.dumps({'seen_event_ids': sorted(seen)[-1000:]}, indent=2), encoding='utf-8')
    print(json.dumps(output['summary']))


if __name__ == '__main__':
    main()
