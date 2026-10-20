"""v1.7.4 combined research: stricter flip sensitivity and paired-distance audit.
No signals, orders, trading, or performance/backtest assertions.
"""
import json
from pathlib import Path
from decimal import Decimal as D
from engine.alpha_walkforward_v171 import history_4h, rank_candidates
from engine.alpha_body_levels_v168 import extract, number
from engine.alpha_flip_v173 import observe_flip_v173, OUTCOMES

PARAMETERS=(
    ('conservative',D('.20'),D('.20'),D('.45')),
    ('baseline',D('.15'),D('.25'),D('.30')),
    ('permissive',D('.10'),D('.30'),D('.20')),
)
HORIZONS=(12,18,24)
GAPS=(D('.5'),D('1'),D('2'))

def replay(bars,lookback=90,stride=24):
    if len(bars)<lookback+max(HORIZONS)+stride*2:
        raise ValueError('INSUFFICIENT_HISTORY')
    if any(y[0]-x[0]!=14400 for x,y in zip(bars,bars[1:])):
        raise ValueError('NONCONTIGUOUS_HISTORY')
    # Shared decision snapshots for all variants prevent differing samples or future leakage.
    rows=[]
    for stop in range(lookback,len(bars)-max(HORIZONS)+1,stride):
        snap=extract('4h',bars[stop-lookback:stop])
        candidates=rank_candidates(snap)
        if not candidates:
            rows.append({'decision_epoch':bars[stop][0],'status':'NO_RESISTANCE'})
            continue
        top=candidates[0];near=min(candidates,key=lambda c:c[1])
        atr=number(snap['atr14_simple_research'])
        close=number(snap['last_close'])
        gap=abs(top[1]-near[1])/atr
        row={'decision_epoch':bars[stop][0],'historical_last_closed_epoch':bars[stop-1][0],
             'status':'EVALUATED','same_level':top[1]==near[1],
             'distance_gap_atr':str(gap),
             'ranked_level':str(top[1]),'nearest_level':str(near[1]),
             'ranked_distance_atr':str((top[1]-close)/atr),
             'nearest_distance_atr':str((near[1]-close)/atr),
             'variants':{}}
        for name,bb,rb,cont in PARAMETERS:
            for horizon in HORIZONS:
                key=name+'_'+str(horizon)
                future=bars[stop:stop+horizon]
                row['variants'][key]={
                    'ranked':observe_flip_v173(top[1],atr,future,bb,rb,cont)['outcome'],
                    'nearest':observe_flip_v173(near[1],atr,future,bb,rb,cont)['outcome']}
        rows.append(row)
    evaluable=[r for r in rows if r['status']=='EVALUATED']
    summaries={}
    for name,_,_,_ in PARAMETERS:
        for horizon in HORIZONS:
            key=name+'_'+str(horizon)
            def summary(items,label):
                outcomes=[r['variants'][key][label] for r in items]
                return {'evaluations':len(outcomes),**{s.lower():outcomes.count(s) for s in OUTCOMES}}
            pairs={}
            for gap in GAPS:
                eligible=[r for r in evaluable if not r['same_level'] and D(r['distance_gap_atr'])<=gap]
                pairs[str(gap)]={'distinct_comparable_pairs':len(eligible),
                    'ranked':summary(eligible,'ranked'),
                    'nearest':summary(eligible,'nearest'),
                    'ranked_only_success':sum(r['variants'][key]['ranked']=='SUCCESSFUL_FLIP' and r['variants'][key]['nearest']!='SUCCESSFUL_FLIP' for r in eligible),
                    'nearest_only_success':sum(r['variants'][key]['nearest']=='SUCCESSFUL_FLIP' and r['variants'][key]['ranked']!='SUCCESSFUL_FLIP' for r in eligible)}
            summaries[key]={'ranked':summary(evaluable,'ranked'),
                            'nearest':summary(evaluable,'nearest'),'distance_matched':pairs}
    return {'version':'alpha-1.7.4-btc-combined-sensitivity','asset':'BTC','timeframe':'4h',
        'historical_closed_bars':len(bars),'lookback_bars':lookback,'stride_bars':stride,
        'decision_count':len(rows),'evaluations':len(evaluable),
        'parameter_sets':[{'name':n,'breakout_atr':str(b),'retest_atr':str(r),'continuation_atr':str(c)} for n,b,r,c in PARAMETERS],
        'horizons_4h_bars':list(HORIZONS),'distance_match_tolerances_atr':[str(x) for x in GAPS],
        'summaries':summaries,'events':rows,
        'limitations':['HISTORICAL_REPLAY_ONLY','SAME_MARKET_EVENTS_ACROSS_VARIANTS',
            'HORIZON_CENSORING','SMALL_PAIRED_SAMPLES','NO_TRUE_OOS_CALIBRATION',
            'PARAMETERS_NOT_VALIDATED','OHLC_INTRABAR_SEQUENCE_UNKNOWN',
            'NO_ORDERFLOW_OR_EXECUTION_PROOF'],
        'research_only':True,'signals':[],'signals_enabled':False,
        'trading_enabled':False,'trade_authorized':False,'backtest_completed':False,
        'continuous_freshness_proven':False,'release_6_0_0_approved':False}

def main():
    bars=history_4h(pages=12)
    report=replay(bars)
    path=Path('artifacts/alpha_swing_v174_btc.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('ALPHA_V174',json.dumps({'bars':len(bars),'evaluations':report['evaluations'],
      'baseline18':report['summaries']['baseline_18'],
      'trades':0,'signals':0}))
if __name__=='__main__':main()
