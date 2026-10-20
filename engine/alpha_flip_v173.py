"""BTC 4h research-only stricter resistance-to-support replay (v1.7.3).
No orders/signals. Closed-candle decisions; no intrabar chronology assumptions.
"""
import json
from decimal import Decimal as D
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h, rank_candidates
from engine.alpha_body_levels_v168 import extract, number

OUTCOMES = ('NO_CONFIRMED_BREAKOUT','BREAKOUT_UNRESOLVED','FAILED_BREAKOUT',
            'BREAKOUT_WITHOUT_RETEST','RETEST_UNRESOLVED','FAILED_RETEST',
            'SUCCESSFUL_FLIP','RETEST_NO_CONFIRMED_CONTINUATION','AMBIGUOUS_RETEST')

def observe_flip_v173(level, atr, future, break_buffer=D('.15'),
                      retest_band=D('.25'), continuation_atr=D('.30')):
    """A flip needs breakout close, next-bar stabilization, then later wick touch,
    a defending close and two subsequent closes, including a close above the
    retest bar's HIGH plus ATR continuation threshold. Future only labels.
    A below-level close on the retest is a failed retest, not a valid defense.
    """
    if level <= 0 or atr <= 0:
        raise ValueError('INVALID_LEVEL_OR_ATR')
    broken = next((i for i,b in enumerate(future) if b[4] >= level+atr*break_buffer),None)
    if broken is None:
        return {'outcome':'NO_CONFIRMED_BREAKOUT','breakout_index':None,'retest_index':None}
    base={'breakout_index':broken,'retest_index':None}
    if broken+1 >= len(future):
        return {'outcome':'BREAKOUT_UNRESOLVED',**base}
    if future[broken+1][4] < level:
        return {'outcome':'FAILED_BREAKOUT',**base}
    band=atr*retest_band
    for j in range(broken+2,len(future)):
        b=future[j]
        if b[4] < level-band:
            return {'outcome':'FAILED_BREAKOUT',**base}
        if b[3] > level+band:
            continue
        base['retest_index']=j
        if b[4] < level:
            return {'outcome':'FAILED_RETEST',**base}
        # If candle pierces substantially below support and closes back above,
        # exact intrabar sequence cannot be demonstrated from OHLC alone.
        if b[3] < level-band:
            return {'outcome':'AMBIGUOUS_RETEST',**base}
        if j+2 >= len(future):
            return {'outcome':'RETEST_UNRESOLVED',**base}
        nxt=future[j+1:j+3]
        if any(x[4] < level for x in nxt):
            return {'outcome':'FAILED_RETEST',**base}
        target=max(level+atr*continuation_atr,b[2])
        if any(x[4] > target for x in nxt):
            return {'outcome':'SUCCESSFUL_FLIP',**base}
        return {'outcome':'RETEST_NO_CONFIRMED_CONTINUATION',**base}
    return {'outcome':'BREAKOUT_WITHOUT_RETEST',**base}

def walkforward_flip_v173(bars,lookback=90,horizon=18,stride=18,distance_tolerance_atr=D('.5')):
    if len(bars)<lookback+horizon+stride*2:
        raise ValueError('INSUFFICIENT_HISTORY')
    if any(b[0]-a[0]!=14400 for a,b in zip(bars,bars[1:])):
        raise ValueError('NONCONTIGUOUS_HISTORY')
    events=[]
    for stop in range(lookback,len(bars)-horizon+1,stride):
        past=bars[stop-lookback:stop]
        future=bars[stop:stop+horizon]
        snap=extract('4h',past)
        choices=rank_candidates(snap)
        if not choices:
            events.append({'decision_epoch':future[0][0],'status':'NO_RESISTANCE'})
            continue
        ranked=choices[0]
        nearest=min(choices,key=lambda x:x[1])
        atr=number(snap['atr14_simple_research'])
        close=number(snap['last_close'])
        row={'decision_epoch':future[0][0],'historical_last_closed_epoch':past[-1][0],
             'atr_at_decision':str(atr),'close_at_decision':str(close),
             'status':'EVALUATED','same_level':ranked[1]==nearest[1]}
        for label,candidate in (('ranked',ranked),('nearest',nearest)):
            score,price,_=candidate
            row[label]={'level':str(price),'heuristic_score':str(score),
                        'distance_atr':str((price-close)/atr),
                        **observe_flip_v173(price,atr,future)}
        row['distance_gap_atr']=str(abs(ranked[1]-nearest[1])/atr)
        row['distance_comparable']=abs(ranked[1]-nearest[1])/atr<=distance_tolerance_atr
        events.append(row)
    def counts(label,subset):
        outcomes=[r[label]['outcome'] for r in subset]
        return {'evaluations':len(outcomes),**{s.lower():outcomes.count(s) for s in OUTCOMES},
                'breakout_observations':sum(s!='NO_CONFIRMED_BREAKOUT' for s in outcomes),
                'retest_observations':sum(s in ('RETEST_UNRESOLVED','FAILED_RETEST','SUCCESSFUL_FLIP',
                          'RETEST_NO_CONFIRMED_CONTINUATION','AMBIGUOUS_RETEST') for s in outcomes)}
    observed=[r for r in events if r['status']=='EVALUATED']
    paired=[r for r in observed if r['distance_comparable'] and not r['same_level']]
    return {'version':'alpha-1.7.3-btc-strict-flip-replay','asset':'BTC','timeframe':'4h',
        'historical_closed_bars':len(bars),'lookback_bars':lookback,
        'horizon_bars':horizon,'stride_bars':stride,
        'ranked_resistance':counts('ranked',observed),
        'nearest_resistance':counts('nearest',observed),
        'distance_matched_distinct_pairs':len(paired),
        'distance_match_tolerance_atr':str(distance_tolerance_atr),
        'distance_matched_ranked':counts('ranked',paired),
        'distance_matched_nearest':counts('nearest',paired),
        'events':events,
        'definition':{
          'breakout':'4h close >= resistance + 0.15 ATR',
          'stabilization':'following 4h close >= resistance',
          'retest':'later 4h low <= resistance + 0.25 ATR',
          'defense':'retest close >= resistance, no deep undercut, next two closes >= resistance',
          'continuation':'one of next two 4h CLOSES > max(retest HIGH, resistance + 0.30 ATR)',
          'intrabar_unknown':'deep wick below resistance - 0.25 ATR is ambiguous'},
        'limitations':['THRESHOLDS_UNCALIBRATED','REPLAY_NOT_EXECUTION_BACKTEST',
            'OHLC_INTRABAR_PATH_UNKNOWN','SMALL_PAIRED_SAMPLES',
            'NO_OUT_OF_SAMPLE_SCORE_CALIBRATION','NO_ORDERFLOW_PROOF',
            'HORIZON_CENSORING'],
        'research_only':True,'signals':[],'signals_enabled':False,
        'trading_enabled':False,'trade_authorized':False,
        'backtest_completed':False,'continuous_freshness_proven':False,
        'release_6_0_0_approved':False}

def main():
    bars=history_4h(pages=8)
    report=walkforward_flip_v173(bars)
    path=Path('artifacts/alpha_swing_v173_btc.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('ALPHA_V173',json.dumps({'bars':len(bars),'ranked':report['ranked_resistance'],
           'nearest':report['nearest_resistance'],
           'distance_matched_distinct_pairs':report['distance_matched_distinct_pairs'],
           'signals':0,'trades':0}))
if __name__=='__main__':main()
