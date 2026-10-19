"""Research-only 4h primary resistance ranking with cross-level event dedup.
Never equate candle volume with actual sell order flow.
"""
from decimal import Decimal as D
from copy import deepcopy
from engine.alpha_body_levels_v168 import number,fmt

def event_groups(zones,period_seconds=14400):
    """One candle/time-window cannot support multiple independent rejection claims."""
    raw=[]
    for zi,z in enumerate(zones):
        for e in z.get('events',[]):
            if isinstance(e.get('start_epoch'),int):
                raw.append((e['start_epoch'],zi,e))
    raw.sort(key=lambda p:p[0])
    clusters=[]
    for row in raw:
        if clusters and row[0]-clusters[-1][-1][0]<period_seconds:
            clusters[-1].append(row)
        else:clusters.append([row])
    accepted={i:[] for i in range(len(zones))}
    conflicts=[]
    for cluster in clusters:
        # Give one event to the closest candidate with the greatest relative move.
        best=max(cluster,key=lambda r:(number(r[2].get('response_atr')) or D(0),-r[1]))
        accepted[best[1]].append(best[2])
        if len(cluster)>1:conflicts.append({'epoch':cluster[0][0],'overlapping_claims':len(cluster),
                                           'assigned_body_level':zones[best[1]]['body_level']})
    return accepted,conflicts

def rank_primary(report):
    if report.get('version')!='alpha-1.6.8-btc-body-wick-probe' or report.get('asset')!='BTC':
        raise ValueError('UNEXPECTED_BASELINE')
    out=deepcopy(report);tfs=report.get('timeframes',{})
    if not all(tf in tfs for tf in ('15m','30m','1h','2h','4h','1D')):
        raise ValueError('MISSING_TIMEFRAME')
    four=tfs['4h'];daily=tfs['1D']
    price=number(four['last_close']);atr=number(four['atr14_simple_research'])
    if price is None or atr is None or atr<=0:raise ValueError('INVALID_REFERENCE')
    zone_candidates=[z for z in four['candidates'] if z.get('type')=='resistance' and number(z.get('body_level')) is not None and number(z['body_level'])>price]
    zone_candidates.sort(key=lambda z:number(z['body_level']))
    kept,conflicts=event_groups(zone_candidates)
    ranked=[]
    daily_candidates=[z for z in daily['candidates'] if z.get('type')=='resistance']
    for i,z in enumerate(zone_candidates):
        p=number(z['body_level']);pivots=int(z.get('body_pivot_count') or 0)
        events=kept[i]
        nr=len(events)
        vol=sum(1 for e in events if number(e.get('candle_rvol20')) is not None and number(e['candle_rvol20'])>=D('1.5'))
        strength=sum(min(number(e.get('response_atr')) or D(0),D(3)) for e in events)
        overlapping=[]
        for d in daily_candidates:
            dp=number(d.get('body_level'))
            if dp is not None and abs(dp-p)<=max(atr*D('.5'),number(daily['atr14_simple_research'])*D('.15')):
                overlapping.append({'daily_body_level':d['body_level'],
                   'daily_rejections_reported':d.get('confirmed_approach_rejections',0)})
        # Heuristic score for comparisons only; no validity threshold or trading use.
        score=min(pivots,5)*10+min(nr,4)*12+min(vol,3)*4+min(strength,D(5))*D(3)+min(len(overlapping),2)*10
        ranked.append({'body_level':z['body_level'],'zone_low':z['zone_low'],'zone_high':z['zone_high'],
          'body_pivots':pivots,'raw_rejections':len(z.get('events',[])),
          'deconflicted_4h_rejections':nr,'supported_volume_events':vol,
          'daily_level_overlap':overlapping,'distance_atr':fmt((p-price)/atr),
          'heuristic_evidence_score':fmt(D(score)),'research_only':True,
          'flow_confirmed':False,'rejection_events':events})
    ranked.sort(key=lambda z:(-number(z['heuristic_evidence_score']),number(z['body_level'])))
    result={'version':'alpha-1.6.9-btc-structure-rank','asset':'BTC','base_version':report['version'],
      'reference_4h_close':four['last_close'],'reference_4h_candle':four['last_closed_identity'],
      'nearest_4h_resistance':zone_candidates[0]['body_level'] if zone_candidates else None,
      'primary_candidate_4h':ranked[0] if ranked else None,'ranked_resistances_4h':ranked,
      'overlapping_4h_claims':conflicts,'method':'HEURISTIC_COMPARISON_NOT_VALIDATED',
      'cross_timeframe_events_are_not_counted_as_independent':True,
      'limits':['ONLY_LAST_100_CANDLES_PER_TF','LEVEL_OVERLAP_NOT_EVENT_PROOF',
       'HEURISTIC_SCORE_NOT_BACKTESTED','NO_TRADE_BY_PRICE_SELL_FLOW',
       'NO_INTERMARKET_EXECUTION_CONFIRMATION'],
      'research_only':True,'signals_enabled':False,'signals':[],
      'trading_enabled':False,'trade_authorized':False,'backtest_completed':False,
      'continuous_freshness_proven':False}
    return result
