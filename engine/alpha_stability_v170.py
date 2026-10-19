"""BTC-only window stability and 4H/1D overlapping-event audit; research only."""
from decimal import Decimal as D
from engine.alpha_body_levels_v168 import extract, number
from engine.alpha_structure_v169 import rank_primary

WINDOWS=(60,70,80,90)

def overlap_events(four_events,daily_events):
    """Report overlapping 4H/1D reaction windows, never claim independent daily corroboration."""
    matching=[];seen=set()
    for a in four_events:
        t=a.get('start_epoch')
        if not isinstance(t,int):continue
        for b in daily_events:
            s=b.get('start_epoch')
            if not isinstance(s,int):continue
            # 4H event inside daily candle or the following 2 4H confirmation bars.
            if s<=t<s+86400+28800:
                k=(t,s)
                if k not in seen:
                    matching.append({'four_hour_epoch':t,'daily_epoch':s,'independent':False})
                    seen.add(k)
    return matching

def audit(base,history_4h,history_daily):
    if base.get('asset')!='BTC' or base.get('version')!='alpha-1.6.8-btc-body-wick-probe':
        raise ValueError('BASE_REPORT_MISMATCH')
    if len(history_4h)<max(WINDOWS) or len(history_daily)<max(WINDOWS):
        raise ValueError('INSUFFICIENT_HISTORY_FOR_STABILITY')
    complete=rank_primary(base)
    reference=complete['primary_candidate_4h']
    if not reference:raise ValueError('NO_PRIMARY_CANDIDATE')
    refprice=number(reference['body_level'])
    fullatr=number(base['timeframes']['4h']['atr14_simple_research'])
    tol=fullatr*D('.25')
    outcomes=[]
    for n in WINDOWS:
        snapshot={**base,'timeframes':dict(base['timeframes'])}
        snapshot['timeframes']['4h']=extract('4h',history_4h[-n:])
        snapshot['timeframes']['1D']=extract('1D',history_daily[-n:]) if n>=60 else base['timeframes']['1D']
        ranking=rank_primary(snapshot)
        selected=ranking['primary_candidate_4h']
        if selected is None:outcomes.append({'window_4h_bars':n,'status':'NO_PRIMARY'});continue
        p=number(selected['body_level'])
        outcomes.append({'window_4h_bars':n,'status':'RANKED','primary_level':selected['body_level'],
          'same_price_area_as_reference':abs(p-refprice)<=tol,
          'primary_score':selected['heuristic_evidence_score'],
          'candidate_count':len(ranking['ranked_resistances_4h'])})
    daily=base['timeframes']['1D']['candidates']
    matching=[]
    for f in complete['ranked_resistances_4h']:
        p=number(f['body_level'])
        for d in daily:
            if d['type']!='resistance':continue
            dp=number(d['body_level'])
            if abs(p-dp)>max(fullatr*D('.5'),number(base['timeframes']['1D']['atr14_simple_research'])*D('.15')):continue
            pairs=overlap_events(f['rejection_events'],d.get('events',[]))
            matching.append({'four_hour_level':f['body_level'],'daily_level':d['body_level'],
                'same_price_area':True,'overlapping_events':pairs,
                'independent_daily_confirmation_proven':False})
    matches=sum(1 for x in outcomes if x.get('same_price_area_as_reference') is True)
    return {'version':'alpha-1.7.0-btc-stability-audit','asset':'BTC',
      'primary_reference_level':reference['body_level'],
      'primary_reference_zone':[reference['zone_low'],reference['zone_high']],
      'window_results':outcomes,'windows_matching_primary_area':matches,
      'windows_tested':len(WINDOWS),'area_tolerance_usdt':str(tol),
      'daily_overlap_checks':matching,
      'cross_tf_independence_confirmed':False,
      'stability_status':'WINDOW_CONSISTENT_RESEARCH_ONLY' if matches==len(WINDOWS) else 'WINDOW_SENSITIVE_RESEARCH_ONLY',
      'method_limits':['ROLLING_SUBSAMPLES_OF_SAME_HISTORY_NOT_OUT_OF_SAMPLE',
        'DAILY_4H_EVENTS_CAN_OVERLAP','ONLY_100_CLOSED_BARS_MAX',
        'HEURISTIC_SCORE_NOT_PROBABILITY','NO_TRADE_BY_PRICE_SELL_FLOW'],
      'research_only':True,'signals':[],'signals_enabled':False,'trading_enabled':False,
      'trade_authorized':False,'backtest_completed':False,'continuous_freshness_proven':False}
