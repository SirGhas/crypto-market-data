"""v1.7.5 research-only multi-timeframe support/resistance belts.
Conservative bounded zones, NO optimized/validated widths, NO trade signals.
"""
import json
from decimal import Decimal as D
from pathlib import Path
from engine.alpha_body_levels_v168 import btc_probe, number

TF_WEIGHT={'15m':1,'30m':2,'1h':3,'2h':4,'4h':6,'1D':9}
TF_SECONDS={'15m':900,'30m':1800,'1h':3600,'2h':7200,'4h':14400,'1D':86400}
# EXPERIMENTAL not calibrated; both absolute percentage and volatility caps required.
EXPERIMENTAL_PCT_CAP=D('0.002')  # 0.20% of price, NOT a trading parameter
ATR_CAP=D('0.35')  # at most 0.35 reference 4h ATR
STRUCTURAL_GAP_FRACTION=D('0.25')

def _fmt(x):
    return format(x.quantize(D('.00000001')).normalize(),'f')

def _validate(levels,price,atr):
    if price is None or atr is None or price<=0 or atr<=0:
        raise ValueError('INVALID_REFERENCE')
    for z in levels:
        if z['side'] not in ('support','resistance') or z['price']<=0:
            raise ValueError('INVALID_LEVEL')
        if z['timeframe'] not in TF_WEIGHT:raise ValueError('UNKNOWN_TIMEFRAME')

def build_belts(levels,price,atr,pct_cap=EXPERIMENTAL_PCT_CAP,atr_cap=ATR_CAP,
                structural_gap_fraction=STRUCTURAL_GAP_FRACTION):
    """No transitive/chain clustering: each proposed belt must pass total width.
    Conservative third gate uses nearest DISTINCT level outside candidate belt,
    and rejects belts when no external structural gap can be evaluated.
    """
    price=number(price);atr=number(atr)
    levels=[{**z,'price':number(z['price'])} for z in levels]
    _validate(levels,price,atr)
    if not (D(0)<pct_cap<D(1) and D(0)<atr_cap and D(0)<structural_gap_fraction<D(1)):
        raise ValueError('INVALID_LIMITS')
    out=[];singles=[]
    for side in ('support','resistance'):
        pool=sorted((z for z in levels if z['side']==side),key=lambda z:z['price'])
        groups=[];cur=[]
        for z in pool:
            if not cur:
                cur=[z];continue
            candidate=cur+[z]
            low=min(x['price'] for x in candidate)
            high=max(x['price'] for x in candidate)
            limit=min(price*pct_cap,atr*atr_cap)
            if high-low<=limit:
                cur=candidate
            else:
                groups.append(cur);cur=[z]
        if cur:groups.append(cur)
        for group in groups:
            low=min(x['price'] for x in group);high=max(x['price'] for x in group)
            width=high-low
            if len(group)<2:
                singles.extend(group);continue
            # Structural gap: distance from belt edge to closest outside same-side level.
            external=[z['price'] for z in pool if z not in group]
            gap=min((low-p if p<low else p-high for p in external if p<low or p>high),default=None)
            passes_gap=(gap is not None and gap>0 and width<=gap*structural_gap_fraction)
            if not passes_gap:
                singles.extend(group);continue
            weights=[D(TF_WEIGHT[z['timeframe']]) for z in group]
            weighted=sum((z['price']*w for z,w in zip(group,weights)),D(0))/sum(weights)
            kinds=sorted(set(z['timeframe'] for z in group),key=lambda x:TF_SECONDS[x])
            strongest=max(TF_WEIGHT[z['timeframe']] for z in group)
            # descriptive tier, NOT statistically calibrated success odds
            # A 4h level plus a 15m echo is NOT sufficient major evidence.
            # Require daily evidence, or a 4h level with independent 2h confirmation.
            tier='MAJOR' if ('1D' in kinds or ('4h' in kinds and '2h' in kinds)) else (
                'INTERMEDIATE' if strongest>=4 else 'MINOR')
            out.append({'side':side,'lower_bound':_fmt(low),'upper_bound':_fmt(high),
                'geometric_center':_fmt((low+high)/2),'evidence_weighted_center':_fmt(weighted),
                'width':_fmt(width),'width_pct':_fmt(width/price*100),
                'width_atr_4h':_fmt(width/atr),'nearest_external_gap':_fmt(gap),
                'source_levels':len(group),'source_timeframes':kinds,'structural_tier':tier,
                'tier_is_heuristic':True,'historically_validated':False,
                'level_sources':[{'price':_fmt(z['price']),'timeframe':z['timeframe']} for z in group]})
    return {'belts':out,'unmerged_levels':[{'side':z['side'],'price':_fmt(z['price']),
             'timeframe':z['timeframe']} for z in singles],
            'limits':{'pct_of_reference_price':_fmt(pct_cap*100),
                      'max_reference_atr_multiplier':_fmt(atr_cap),
                      'max_fraction_of_external_gap':_fmt(structural_gap_fraction),
                      'no_external_gap':'DO_NOT_MERGE'},
            'parameters_calibrated':False}

def assemble(probe):
    if probe.get('asset')!='BTC' or probe.get('primary_timeframe')!='4h':
        raise ValueError('UNEXPECTED_PROBE')
    tf=probe['timeframes'];reference=tf['4h']
    price=number(reference['last_close']);atr=number(reference['atr14_simple_research'])
    levels=[]
    for name in TF_WEIGHT:
        for z in tf[name]['candidates']:
            p=number(z.get('body_level'))
            if p is not None and z['type'] in ('support','resistance'):
                levels.append({'side':z['type'],'price':p,'timeframe':name})
    results=build_belts(levels,price,atr)
    return {'version':'alpha-1.7.5-btc-mtf-belt-prototype',
      'asset':'BTC','reference_price':_fmt(price),'reference_atr_4h':_fmt(atr),
      'timeframes':list(TF_WEIGHT),'candidate_levels':len(levels),**results,
      'limitations':['ONLY_100_CANDLES_PER_TIMEFRAME','PERCENT_CAP_EXPERIMENTAL_NOT_CALIBRATED',
        'SAME_PRICE_EPISODES_NOT_INDEPENDENT','NO_HISTORICAL_OOS_BELT_VALIDATION',
        'MAJOR_MINOR_TIERS_HEURISTIC','NO_WEEKLY_MONTHLY_OR_ALL_TIME_HIGH_VERIFICATION',
        'NO_EXECUTION_OR_ORDERFLOW_PROOF'],
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,'backtest_completed':False,
      'continuous_freshness_proven':False,'release_6_0_0_approved':False}

def main():
    report=assemble(btc_probe())
    p=Path('artifacts/alpha_swing_v175_btc_belts.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V175',json.dumps({'candidates':report['candidate_levels'],
      'belts':len(report['belts']),'unmerged':len(report['unmerged_levels']),
      'signals':0,'trades':0}))
if __name__=='__main__':main()
