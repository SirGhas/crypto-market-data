"""Causal, research-only BTC 4H resistance -> support flip audit."""
import json
from decimal import Decimal as D
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h,rank_candidates
from engine.alpha_body_levels_v168 import extract,number

def observe_flip(level,atr,future,break_buffer=D('.15'),retest_band=D('.25'),bounce_atr=D('.30')):
    """No future knowledge at decision. One candidate, one bounded observation window.
    Intrabar path unknown: same candle cross-and-reclaim is ambiguous.
    """
    upper=level+atr*break_buffer
    band=atr*retest_band
    broken=None
    for i,b in enumerate(future):
        if b[4]>=upper:broken=i;break
    if broken is None:return {'outcome':'NO_CONFIRMED_BREAKOUT','breakout_index':None,'retest_index':None}
    if broken+1>=len(future):return {'outcome':'BREAKOUT_UNRESOLVED','breakout_index':broken,'retest_index':None}
    if future[broken+1][4]<level:
        return {'outcome':'FAILED_BREAKOUT','breakout_index':broken,'retest_index':None}
    # Stabilization requires next closed candle above the zone.
    retest=None
    for j in range(broken+2,len(future)):
        b=future[j]
        if b[4]<level-band:
            return {'outcome':'FAILED_BREAKOUT','breakout_index':broken,'retest_index':retest}
        if b[3]<=level+band:
            retest=j
            if b[4]<level:return {'outcome':'RETEST_UNRESOLVED','breakout_index':broken,'retest_index':j}
            if j+2>=len(future):
                return {'outcome':'RETEST_UNRESOLVED','breakout_index':broken,'retest_index':j}
            nexttwo=future[j+1:j+3]
            if any(x[4]<level-band for x in nexttwo):
                return {'outcome':'FAILED_RETEST','breakout_index':broken,'retest_index':j}
            if any(x[2]>=level+atr*bounce_atr for x in nexttwo):
                return {'outcome':'SUCCESSFUL_FLIP','breakout_index':broken,'retest_index':j}
            return {'outcome':'RETEST_NO_CONFIRMED_CONTINUATION','breakout_index':broken,'retest_index':j}
    return {'outcome':'BREAKOUT_WITHOUT_RETEST','breakout_index':broken,'retest_index':None}

def walkforward_flip(bars,lookback=90,horizon=18,stride=18):
    if len(bars)<lookback+horizon+stride*2:raise ValueError('INSUFFICIENT_HISTORY')
    if any(b[0]-a[0]!=14400 for a,b in zip(bars,bars[1:])):raise ValueError('NONCONTIGUOUS_HISTORY')
    events=[]
    for stop in range(lookback,len(bars)-horizon+1,stride):
        past=bars[stop-lookback:stop];future=bars[stop:stop+horizon]
        snap=extract('4h',past)
        choices=rank_candidates(snap)
        if not choices:
            events.append({'decision_epoch':future[0][0],'status':'NO_RESISTANCE'});continue
        ranked=choices[0];nearest=min(choices,key=lambda x:x[1])
        atr=number(snap['atr14_simple_research'])
        row={'decision_epoch':future[0][0],'historical_last_closed_epoch':past[-1][0],
             'evaluation_horizon_bars':len(future),'status':'EVALUATED'}
        for label,candidate in [('ranked',ranked),('nearest',nearest)]:
            score,price,zone=candidate
            result=observe_flip(price,atr,future)
            row[label]={'level':str(price),'heuristic_score':str(score),**result}
        row['same_level']=ranked[1]==nearest[1]
        events.append(row)
    def metrics(label):
        outcomes=[r[label]['outcome'] for r in events if r.get('status')=='EVALUATED']
        d={'evaluations':len(outcomes)}
        for status in ['NO_CONFIRMED_BREAKOUT','BREAKOUT_UNRESOLVED','FAILED_BREAKOUT',
                       'BREAKOUT_WITHOUT_RETEST','RETEST_UNRESOLVED','FAILED_RETEST',
                       'SUCCESSFUL_FLIP','RETEST_NO_CONFIRMED_CONTINUATION']:
            d[status.lower()]=outcomes.count(status)
        d['confirmed_breakout_observations']=len(outcomes)-d['no_confirmed_breakout']
        d['retest_observations']=sum(outcome in ('RETEST_UNRESOLVED','FAILED_RETEST','SUCCESSFUL_FLIP',
                                                 'RETEST_NO_CONFIRMED_CONTINUATION') for outcome in outcomes)
        return d
    return {'version':'alpha-1.7.2-btc-resistance-support-flip','asset':'BTC','timeframe':'4h',
       'historical_closed_bars':len(bars),'lookback_bars':lookback,'horizon_bars':horizon,
       'stride_bars':stride,'ranked_resistance':metrics('ranked'),
       'nearest_resistance':metrics('nearest'),'events':events,
       'definition':{'breakout':'4h close >= resistance + 0.15 ATR',
          'stabilization':'next 4h candle closes at or above resistance',
          'retest':'later 4h low reaches resistance + 0.25 ATR',
          'support_defense':'retest closes >= resistance and next two closes not below resistance - 0.25 ATR',
          'continuation':'within next two bars high >= resistance + 0.30 ATR'},
       'limitations':['HEURISTIC_THRESHOLDS_NOT_CALIBRATED',
           '4H_OHLC_NO_INTRABAR_SEQUENCE','RETEST_TIMING_CENSORED_BY_HORIZON',
           'EVENT_SAMPLES_OVERLAP_ACROSS_METHODS','NO_ORDERFLOW_PROOF',
           'REPLAY_ONLY_NOT_EXECUTION_BACKTEST'],
       'research_only':True,'signals':[],'signals_enabled':False,'trading_enabled':False,
       'trade_authorized':False,'backtest_completed':False,'continuous_freshness_proven':False}

def main():
    bars=history_4h(pages=8)
    report=walkforward_flip(bars)
    output=Path('artifacts/alpha_swing_v172_btc.json');output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('ALPHA_V172',json.dumps({'bars':len(bars),'ranked':report['ranked_resistance'],
        'nearest':report['nearest_resistance'],'signals':0,'trades':0}))
if __name__=='__main__':main()
