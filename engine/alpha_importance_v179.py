"""v1.7.9 research-only multi-timeframe structural level importance.

Scores represent descriptive structural evidence, NOT reversal probabilities.
Avoid counting duplicate cross-timeframe levels as independent events.
"""
import json
from decimal import Decimal as D
from pathlib import Path
from engine.alpha_body_levels_v168 import btc_probe, number
from engine.alpha_belts_v175 import build_belts, TF_WEIGHT,TF_SECONDS

def classify(tf, confirmations=()):
    sources=set(confirmations)|{tf}
    if '1D' in sources or ('4h' in sources and '2h' in sources):
        return 'MAJOR'
    if '4h' in sources or '2h' in sources:return 'INTERMEDIATE'
    return 'MINOR'

def score_level(timeframe,pivots,rejections):
    if timeframe not in TF_WEIGHT:raise ValueError('UNKNOWN_TIMEFRAME')
    # bounded heuristic, duplicates or overlapping episodes are NOT multiplied
    return min(100,TF_WEIGHT[timeframe]*7+min(int(pivots),3)*3+
               min(int(rejections),2)*4)

def build_map(probe):
    if probe.get('asset')!='BTC' or probe.get('primary_timeframe')!='4h':
        raise ValueError('INVALID_PROBE')
    tfs=probe['timeframes']; ref=tfs['4h']
    close=number(ref['last_close']);atr=number(ref['atr14_simple_research'])
    if close is None or atr is None or close<=0 or atr<=0:raise ValueError('INVALID_REFERENCE')
    levels=[]
    for tf in TF_WEIGHT:
        for c in tfs[tf]['candidates']:
            if c.get('type') not in ('support','resistance'):continue
            p=number(c.get('body_level'))
            if p is None or p<=0:continue
            s=score_level(tf,c.get('body_pivot_count') or 0,
                           c.get('confirmed_approach_rejections') or 0)
            levels.append({'side':c['type'],'price':p,'timeframe':tf,'score':s,
                           'pivots':int(c.get('body_pivot_count') or 0),
                           'rejections_reported':int(c.get('confirmed_approach_rejections') or 0)})
    belts=build_belts(levels,close,atr)
    # Only structural tier and score annotations: never override belt width gates.
    for belt in belts['belts']:
        matches=[x for x in levels if x['side']==belt['side']
                 and D(belt['lower_bound'])<=x['price']<=D(belt['upper_bound'])
                 and x['timeframe'] in belt['source_timeframes']]
        belt['structural_tier']=classify(matches[0]['timeframe'],(x['timeframe'] for x in matches[1:]))
        belt['importance_score']=max(x['score'] for x in matches) if matches else 0
        belt['importance_score_type']='DESCRIPTIVE_HEURISTIC_NOT_PROBABILITY'
        belt['rejection_events_are_independent']=False
    annotated=[]
    for item in belts['unmerged_levels']:
        matches=[x for x in levels if x['side']==item['side']
                 and str(x['price'])==str(D(item['price']))
                 and x['timeframe']==item['timeframe']]
        source=matches[0] if matches else None
        annotated.append({**item,'structural_tier':classify(item['timeframe']),
               'importance_score':source['score'] if source else 0,
               'importance_score_type':'DESCRIPTIVE_HEURISTIC_NOT_PROBABILITY'})
    return {'version':'alpha-1.7.9-btc-mtf-importance','asset':'BTC',
       'reference_price':str(close),'reference_atr_4h':str(atr),
       'belts':belts['belts'],'standalone_levels':annotated,'candidate_levels':len(levels),
       'tier_definition':{'MAJOR':'daily level or paired 4h+2h origins',
          'INTERMEDIATE':'4h or 2h origin','MINOR':'15m, 30m or 1h origin'},
       'limits':belts['limits'],
       'limitations':['NO_ALL_TIME_HIGH_VERIFICATION','NO_WEEKLY_MONTHLY_LEVELS',
           'MULTI_TIMEFRAME_SNAPSHOTS_NOT_HISTORICAL_OOS',
           'OVERLAPPING_REACTIONS_NOT_INDEPENDENT',
           'LEVEL_SCORE_NOT_CALIBRATED','BELT_WIDTHS_EXPERIMENTAL',
           'NO_EXECUTION_BACKTEST_OR_SIGNALS'],
       'research_only':True,'signals':[],'signals_enabled':False,
       'trading_enabled':False,'trade_authorized':False,'backtest_completed':False,
       'continuous_freshness_proven':False,'release_6_0_0_approved':False}

def main():
    data=build_map(btc_probe())
    p=Path('artifacts/alpha_swing_v179_btc_importance.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    print('ALPHA_V179',json.dumps({'levels':data['candidate_levels'],
       'belts':len(data['belts']),'standalone':len(data['standalone_levels']),
       'signals':0,'trades':0}))
if __name__=='__main__':main()
