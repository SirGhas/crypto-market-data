"""Research-only v0.7 weighted screener. Never authorizes a trade."""
from decimal import Decimal, InvalidOperation

WEIGHTS = {'static_levels':30, 'native_volume':30, 'sma233':20, 'rsi14':10, 'higher_timeframe':10}
ORDER = ('5m','15m','1h','4h')
def dec(x):
    try:
        d=Decimal(str(x))
        return d if d.is_finite() else None
    except (InvalidOperation,ValueError,TypeError): return None

def side_of(x):
    if x.get('status')!='RESEARCH_VALIDATED':return None
    v=x.get('native_volume_price_action',{})
    if v.get('closed_above_prior_resistance_20') is True and v.get('closed_below_prior_support_20') is not True:return 'LONG'
    if v.get('closed_below_prior_support_20') is True and v.get('closed_above_prior_resistance_20') is not True:return 'SHORT'
    return None

def grade(tf,asset,all_tf):
    x=all_tf.get(tf,{}).get(asset,{})
    out={'status':'BLOCKED','side':'NONE','research_score':None,'research_tier':None,
         'scoring_policy':'PROVISIONAL_V07_NOT_BACKTEST_CALIBRATED','components':{},
         'blocking_reasons':[],'signal_authorized':False}
    if x.get('status')!='RESEARCH_VALIDATED':
        out['blocking_reasons'].append('INVALID_INPUT');return out
    s=x.get('sma_close',{});r=x.get('rsi14',{});v=x.get('native_volume_price_action',{})
    ids=(s.get('identity'),r.get('identity'),v.get('identity'))
    if len(set(ids))!=1 or not all(ids) or s.get('status')!='SMA_CLOSE_VALIDATED' or r.get('status')!='RSI_WILDER_CLOSE_VALIDATED' or v.get('status')!='NATIVE_VOLUME_PRICE_ACTION_VALIDATED':
        out['blocking_reasons'].append('INDICATOR_IDENTITY_OR_STATUS_MISMATCH');return out
    if s.get('sma_source')!='CLOSE' or r.get('source')!='CLOSE' or v.get('volume_source')!='OKX_NATIVE_BASE_VOLUME':
        out['blocking_reasons'].append('SOURCE_MISMATCH');return out
    sma=s.get('smas',{}).get('SMA233',{})
    if sma.get('value') is None or dec(r.get('value')) is None or dec(v.get('rvol20')) is None:
        out['blocking_reasons'].append('MISSING_REQUIRED_DATA');return out
    if dec(r['value']) < 0 or dec(r['value']) > 100 or dec(v['rvol20']) < 0:
        out['blocking_reasons'].append('OUT_OF_RANGE_DATA');return out
    side=side_of(x);out['side']=side or 'NONE'
    aligned=lambda y: (y.get('sma_close',{}).get('smas',{}).get('SMA233',{}).get('close_above') is True and y.get('sma_close',{}).get('smas',{}).get('SMA233',{}).get('slope')=='UP') if side=='LONG' else (y.get('sma_close',{}).get('smas',{}).get('SMA233',{}).get('close_below') is True and y.get('sma_close',{}).get('smas',{}).get('SMA233',{}).get('slope')=='DOWN')
    # Never score an arbitrary price movement as a confirmed break.
    level_pts=30 if side else 0
    rv=dec(v['rvol20'])
    volume_pts=30 if rv>=2 else 22 if rv>=Decimal('1.5') else 15 if rv>=1 else 0
    sma_pts=20 if side and aligned(x) else 0
    ri=dec(r['value'])
    rsi_pts=10 if side and ((side=='LONG' and Decimal('50')<=ri<Decimal('70')) or (side=='SHORT' and Decimal('30')<ri<=Decimal('50'))) else 0
    higher={'5m':'15m','15m':'1h','1h':'4h','4h':None}[tf]
    ht=all_tf.get(higher,{}).get(asset,{}) if higher else {}
    ht_pts=10 if side and higher and ht.get('status')=='RESEARCH_VALIDATED' and aligned(ht) else 0
    out['components']={'static_levels':level_pts,'native_volume':volume_pts,'sma233':sma_pts,'rsi14':rsi_pts,'higher_timeframe':ht_pts}
    score=sum(out['components'].values());out['research_score']=score
    out['research_tier']='GREEN' if score>=80 else 'BLUE' if score>=70 else 'YELLOW' if score>=60 else 'BELOW_60'
    if not side:out['blocking_reasons'].append('NO_CONFIRMED_STATIC_LEVEL_BREAK')
    if rv<Decimal('1.5'):out['blocking_reasons'].append('RVOL_LT_1_5')
    if not side or not aligned(x):out['blocking_reasons'].append('SMA233_DIRECTION_NOT_CONFIRMED')
    if not higher:out['blocking_reasons'].append('NO_HIGHER_TIMEFRAME')
    elif not ht_pts:out['blocking_reasons'].append('HIGHER_TIMEFRAME_NOT_CONFIRMED')
    out['blocking_reasons']+=['TRADE_RR_NOT_VALIDATED','SPREAD_DEPTH_NOT_VALIDATED','CROSS_RUN_FRESHNESS_NOT_PROVEN','RESEARCH_ONLY']
    out['status']='RESEARCH_GRADED'
    return out

def analyze(report):
    blocks=report.get('timeframes',{})
    if report.get('version')!='alpha-0.6-rsi-volume' or report.get('research_only') is not True or report.get('trading_enabled') is not False or report.get('signals_enabled') is not False:
        raise ValueError('UNSAFE_OR_WRONG_INPUT')
    assets=sorted(set().union(*(set(x.keys()) for x in blocks.values())))
    screens={tf:{a:grade(tf,a,blocks) for a in assets} for tf in ORDER}
    ranked=sorted([{'asset':a,'timeframe':tf,**x} for tf,b in screens.items() for a,x in b.items() if x['status']=='RESEARCH_GRADED'],
                  key=lambda v:(-v['research_score'],v['asset'],ORDER.index(v['timeframe'])))
    return {'version':'alpha-0.7-research-scoring','source_version':report['version'],
            'source_run_id':report.get('run_id'),'source_time_utc':report.get('timestamp_utc'),
            'research_only':True,'signals_enabled':False,'trading_enabled':False,'release_6_0_0_approved':False,
            'scores_computed':True,'scores_are_trade_probabilities':False,'backtest_completed':False,
            'continuous_freshness_proven':False,'signals':[],
            'weights':WEIGHTS,'tier_thresholds':{'GREEN':80,'BLUE':70,'YELLOW':60},
            'screens':screens,'ranked_research_events':[x for x in ranked if x['side']!='NONE'],
            'totals':{'expected':len(assets)*len(ORDER),'graded':len(ranked),'blocked':len(assets)*len(ORDER)-len(ranked),
                      'research_level_events':sum(x['side']!='NONE' for x in ranked),
                      'signals':0},'outcome':'RESEARCH_SCORES_NOT_SIGNALS'}
