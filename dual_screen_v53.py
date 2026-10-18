"""Research-only two-tier screening of CLOSED spot candles. Python 3.12 stdlib."""
import datetime as dt
import json
from pathlib import Path

ROOT = Path('data')
COINS = ('ETH', 'BNB', 'SOL', 'LTC', 'LINK', 'XRP', 'AVAX', 'SUI', 'AAVE','ZEC')
FRAMES = {'4h': 14400, '1h': 3600, '15m': 900}
WEIGHTS = {'static_levels': 30, 'volume': 25, 'trend_4h': 15, 'risk_reward': 15,
           'relative_btc': 5, 'lower_timeframes': 5, 'btc_and_dominance': 5}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def fresh(frame, seconds, now):
    if frame.get('status') != 'available':
        return False
    candles = frame.get('candles', [])
    if len(candles) < 234:
        return False
    end = candles[-1]['t'] + seconds
    return 0 <= now - end <= seconds + 300


def avg_volume(candles):
    baseline = sum(c['v'] for c in candles[-21:-1]) / 20
    return candles[-1]['v'] / baseline if baseline > 0 else None


def static_levels(candles, price, tolerance=0.012):
    """Multi-touch pivot clustering; no forming candle, no future candles.

    Pivot at i uses two older and two newer *closed* candles. Touches must be
    separated by >=3 bars; this is a heuristic, NOT verified institutional S/R.
    """
    history = candles[-100:-1]
    pivots = []
    for i in range(2, len(history) - 2):
        c = history[i]
        if c['l'] <= min(history[j]['l'] for j in range(i-2, i+3)):
            pivots.append(('support', c['l'], i))
        if c['h'] >= max(history[j]['h'] for j in range(i-2, i+3)):
            pivots.append(('resistance', c['h'], i))
    levels = {}
    for typ in ('support', 'resistance'):
        candidates = [(v, i) for t, v, i in pivots if t == typ and v > 0]
        clusters = []
        for value, index in candidates:
            matching = next((cl for cl in clusters if abs(value / cl['center'] - 1) <= tolerance), None)
            if matching is None:
                clusters.append({'center': value, 'touches': [index], 'values': [value]})
            elif all(abs(index - j) >= 3 for j in matching['touches']):
                matching['touches'].append(index)
                matching['values'].append(value)
                matching['center'] = sum(matching['values']) / len(matching['values'])
        valid = [cl for cl in clusters if len(cl['touches']) >= 2 and
                 ((cl['center'] < price) if typ == 'support' else (cl['center'] > price))]
        if valid:
            best = min(valid, key=lambda cl: abs(price / cl['center'] - 1))
            levels[typ] = round(best['center'], 10)
            levels[typ+'_touches'] = len(best['touches'])
    return levels


def evaluate(coin, market, legacy, now):
    frames = market.get('pairs', {}).get(coin+'USDT', {}).get('frames', {})
    if any(not fresh(frames.get(tf, {}), seconds, now) for tf, seconds in FRAMES.items()):
        return {'coin': coin, 'tier': 'blocked', 'score': None,
                'reasons': ['missing_or_stale_required_closed_candles']}
    four, one, fifteen = (frames[tf]['candles'] for tf in ('4h','1h','15m'))
    price = one[-1]['c']
    levels = static_levels(four, price)
    # Provisional bounds are displayed separately, never awarded validated S/R points.
    provisional = four[-21:-1]
    provisional_support = min(c['l'] for c in provisional)
    provisional_resistance = max(c['h'] for c in provisional)
    support, resistance = levels.get('support'), levels.get('resistance')
    rr = ((resistance-price)/(price-support)
          if support and resistance and support < price < resistance else None)
    v1, v4 = avg_volume(one), avg_volume(four)
    volume_score = (15 if v1 is not None and v1 >= 1.3 else
                    10 if v1 is not None and v1 >= 1.0 else 5 if v1 is not None and v1 >= 0.8 else 0)
    volume_score += (10 if v4 is not None and v4 >= 1.3 else
                     6 if v4 is not None and v4 >= 1.0 else 3 if v4 is not None and v4 >= 0.8 else 0)
    static_score = (15 if support is not None else 0) + (15 if resistance is not None else 0)
    sma4 = sum(c['c'] for c in four[-233:]) / 233
    sma1 = sum(c['c'] for c in one[-233:]) / 233
    sma15 = sum(c['c'] for c in fifteen[-233:]) / 233
    trend_score = (10 if four[-1]['c'] > sma4 else 0) + (5 if four[-1]['c'] > four[-5]['c'] else 0)
    rr_score = 15 if rr is not None and rr >= 3 else 12 if rr is not None and rr >= 2.5 else 8 if rr is not None and rr >= 2 else 0
    lower_score = (3 if one[-1]['c'] > sma1 else 0) + (2 if fifteen[-1]['c'] > sma15 else 0)
    cross = market.get('pairs', {}).get(coin+'BTC', {}).get('frames', {}).get('4h', {})
    relative = None
    if fresh(cross, 14400, now):
        cs = cross['candles']
        relative = cs[-1]['c'] > sum(c['c'] for c in cs[-233:]) / 233
    relative_score = 5 if relative else 0
    btc = market.get('pairs', {}).get('BTCUSDT', {}).get('frames', {}).get('4h', {})
    btc_ok = False
    if fresh(btc, 14400, now):
        bs = btc['candles']
        btc_ok = bs[-1]['c'] > sum(c['c'] for c in bs[-233:]) / 233
    # CoinGecko snapshots are not verified BTC.D/USDT.D trend data: max 2/5.
    macro_score = 2 if btc_ok else 0
    components = {'static_levels': static_score, 'volume': volume_score,
                  'trend_4h': trend_score, 'risk_reward': rr_score,
                  'relative_btc': relative_score, 'lower_timeframes': lower_score,
                  'btc_and_dominance': macro_score}
    score = sum(components.values())
    reasons = []
    if support is None or resistance is None:
        reasons.append('validated_multitouch_support_or_resistance_missing')
    if volume_score < 15:
        reasons.append('volume_below_first_tier_minimum')
    if relative is None:
        reasons.append('btc_cross_missing_or_stale')
    reasons.append('dominance_trend_unverified')
    if rr is None:
        reasons.append('risk_reward_not_valid_without_both_validated_levels')
    elif rr < 2:
        reasons.append('risk_reward_below_2')
    # No trade authorization from scoring. Tier 1 still requires critical gates.
    if score >= 80 and static_score >= 20 and volume_score >= 15 and rr is not None and rr >= 2:
        tier = 'tier_1_priority_watch'
    elif score >= 70 and rr is not None and rr >= 2.5:
        tier = 'tier_2_conditional_watch'
    elif score >= 60 and rr is not None and rr >= 3:
        tier = 'tier_2_conditional_watch'
    else:
        tier = 'below_threshold_watch_only'
    return {'coin': coin, 'tier': tier, 'score': score, 'score_components': components,
            'weights': WEIGHTS, 'reference_price_usdt': price,
            'reference_price_kind': 'last_closed_1h_not_live',
            'closed_1h_at_utc': frames['1h']['last_closed_at_utc'],
            'static_levels': levels, 'provisional_20x4h_bounds_not_validated': {
                'support': provisional_support, 'resistance': provisional_resistance},
            'risk_reward_validated_levels': round(rr, 3) if rr is not None else None,
            'relative_volume_1h': round(v1, 3) if v1 is not None else None,
            'relative_volume_4h': round(v4, 3) if v4 is not None else None,
            'relative_strength_btc': relative, 'reasons': reasons,
            'sources': {tf: frames[tf]['source'] for tf in FRAMES},
            'notes': 'Heuristic static pivots, not verified order book; excludes fees/slippage. No trade instruction.'}


def main():
    market = load(ROOT/'multisource_market.json')
    now = dt.datetime.now(dt.timezone.utc)
    generated = dt.datetime.fromisoformat(market['generated_at_utc'].replace('Z', '+00:00'))
    if not 0 <= (now-generated).total_seconds() <= 5400:
        raise RuntimeError('Source snapshot is stale; refusing to publish new report')
    evaluations = [evaluate(coin, market, None, now.timestamp()) for coin in COINS]
    ranked = sorted([e for e in evaluations if e['score'] is not None], key=lambda e: (e['score'], e['risk_reward_validated_levels'] or -1), reverse=True)
    first = [e for e in ranked if e['tier']=='tier_1_priority_watch']
    second = [e for e in ranked if e['tier']=='tier_2_conditional_watch']
    out = {'schema_version': 53, 'generated_at_utc': now.isoformat(),
           'source_generated_at_utc': market['generated_at_utc'],
           'mode': 'two_tier_research_only_no_orders_no_push_notifications',
           'weights': WEIGHTS, 'tier_1_top_three': first[:3], 'tier_2_top_three': second[:3],
           'closest_three_below_threshold_not_buy_signals': [e for e in ranked if e['tier']=='below_threshold_watch_only'][:3],
           'evaluations': evaluations, 'summary': {'scanned': len(evaluations),
               'blocked': sum(e['tier']=='blocked' for e in evaluations),
               'tier_1': len(first), 'tier_2': len(second)},
           'limitations': ['Score is not win probability', 'Multi-touch pivot heuristic needs backtesting',
                           'No verified BTC.D/USDT.D candle trend', 'No live prices or trade execution',
                           'Partial BTC crosses are not assumed bullish']}
    path = ROOT/'dual_screen_v53.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(out['summary']))

if __name__ == '__main__':
    main()
