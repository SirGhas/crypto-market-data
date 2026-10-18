"""Research-only multi-timeframe discovery, independent 4h reference and early watch."""
from decimal import Decimal as D
from copy import deepcopy
from engine.alpha_swing_v11 import score_setup

TFS=('15m','30m','1h','2h','4h','1D')
EARLY=('15m','30m','1h','2h')
WEIGHTS={'15m':10,'30m':15,'1h':20,'2h':25,'4h':30}
RESEARCH_FLAGS={'research_only':True,'signals_authorized':False,'trade_authorized':False}

def tf_condition(a):
    if a.get('status')!='VALIDATED':return None
    sma=a['sma_close']['SMA233']
    tests={'close_above_sma233':bool(sma['close_above']),
           'sma233_slope_up':sma['slope']=='UP',
           'rsi14_above_50':D(a['rsi14'])>50,
           'rvol20_at_least_1':D(a['rvol20'])>=1,
           'static_breakout_20':bool(a['broke_resistance_20'])}
    # This 0-100 local strength is descriptive, not calibrated trade probability.
    score=sum((20 if t else 0) for t in tests.values())
    return {'score':score,'components':tests,'identity':a['identity']}

def score_watch(audits):
    cond={tf:tf_condition(audits[tf]) for tf in WEIGHTS}
    if any(v is None for v in cond.values()):
        return {'status':'BLOCKED','reason':'ONE_OR_MORE_TIMEFRAMES_INVALID','early_score':None,
                'alignment_score':None,'components':cond,**RESEARCH_FLAGS}
    early_numerator=sum(cond[tf]['score']*WEIGHTS[tf] for tf in EARLY)
    early_score=D(early_numerator)/D(sum(WEIGHTS[tf] for tf in EARLY))
    aligned=D(sum(cond[tf]['score']*WEIGHTS[tf] for tf in WEIGHTS))/100
    return {'status':'RESEARCH_WATCH_VALID','early_score':str(early_score),
            'alignment_score':str(aligned),'components':cond,
            'weights':WEIGHTS,'early_weight_total':70,
            'not_trade_probability':True,'independent_of_reference_score':True,**RESEARCH_FLAGS}

def snapshot(markets,now,previous=None):
    assets=sorted({a for bucket in markets.values() for a in bucket})
    report={'version':'alpha-1.2-multi-timeframe-watch','run_epoch':now,
            'primary_timeframe':'4h','context_timeframe':'1D',
            'early_timeframes':list(EARLY),'closed_timeframes':list(TFS),
            'signals':[],'signals_enabled':False,'trading_enabled':False,
            'release_6_0_0_approved':False,'continuous_freshness_proven':False,
            'backtest_completed':False,'research_only':True,'assets':{},
            'watch_events':[],'cross_run':{'status':'NO_PREVIOUS_BASELINE','advanced':0,'unchanged':0,'anomalies':[]},
            'note':'Scores measure weighted technical conditions, not the probability of profit.'}
    if previous is not None and previous.get('version')!='alpha-1.2-multi-timeframe-watch':
        raise ValueError('INCOMPATIBLE_BASELINE')
    for asset in assets:
        aud={tf:deepcopy(markets.get(tf,{}).get(asset,{'status':'BLOCKED','reason':'MISSING'})) for tf in TFS}
        reference=score_setup(aud['4h'],aud['1D'],aud['1h'],aud['2h'])
        watch=score_watch(aud)
        item={'timeframes':aud,'reference_score':reference,'watch_score':watch,**RESEARCH_FLAGS}
        report['assets'][asset]=item
        if previous is None:continue
        prev=previous.get('assets',{}).get(asset)
        if not prev:continue
        changed=[]
        for tf in TFS:
            newer=aud[tf];older=prev.get('timeframes',{}).get(tf,{})
            if newer.get('status')!='VALIDATED' or older.get('status')!='VALIDATED':
                report['cross_run']['anomalies'].append({'asset':asset,'timeframe':tf,'reason':'BLOCKED_COMPARISON'})
                continue
            new_t=newer.get('last_closed_start_epoch');old_t=older.get('last_closed_start_epoch')
            if not isinstance(new_t,int) or not isinstance(old_t,int) or new_t<old_t:
                report['cross_run']['anomalies'].append({'asset':asset,'timeframe':tf,'reason':'CANDLE_REGRESSION'})
                continue
            if new_t==old_t:
                report['cross_run']['unchanged']+=1
                # Within same candle identity, fixed indicator values must not drift.
                for field in ('close','rsi14','rvol20'):
                    if newer.get(field)!=older.get(field):
                        report['cross_run']['anomalies'].append({'asset':asset,'timeframe':tf,'reason':'SAME_CANDLE_REVISION','field':field})
            else:
                report['cross_run']['advanced']+=1
                changed.append(tf)
        if report['cross_run']['anomalies']:continue
        pw=prev.get('watch_score',{});pr=prev.get('reference_score',{})
        # Events are only changes on a new closed candle; no alert on baseline first run.
        old_early=pw.get('early_score');new_early=watch.get('early_score')
        if any(tf in changed for tf in EARLY) and old_early is not None and new_early is not None:
            delta=D(new_early)-D(old_early)
            new_bucket=int(D(new_early)//10);old_bucket=int(D(old_early)//10)
            if abs(delta)>=10 or new_bucket!=old_bucket:
                report['watch_events'].append({'asset':asset,'type':'EARLY_CHANGE','old':old_early,
                    'new':new_early,'delta':str(delta),'timeframes_changed':[tf for tf in EARLY if tf in changed],
                    'closed_candle_ids':{tf:aud[tf].get('identity') for tf in EARLY if tf in changed},**RESEARCH_FLAGS})
        old_ref=pr.get('score');new_ref=reference.get('score')
        if '4h' in changed and old_ref is not None and new_ref is not None and reference.get('tier')!=pr.get('tier'):
            report['watch_events'].append({'asset':asset,'type':'REFERENCE_TIER_CHANGE',
                'old':old_ref,'new':new_ref,'old_tier':pr.get('tier'),'new_tier':reference.get('tier'),
                'closed_candle_ids':{'4h':aud['4h'].get('identity')},**RESEARCH_FLAGS})
    if previous is not None:
        cr=report['cross_run'];cr['status']='ANOMALIES' if cr['anomalies'] else 'COMPARED'
        if cr['anomalies']:report['watch_events']=[]
    report['totals']={'assets':len(assets),'validated_timeframes':sum(a['status']=='VALIDATED' for i in report['assets'].values() for a in i['timeframes'].values()),
        'expected_timeframes':len(assets)*len(TFS),'reference_graded':sum(i['reference_score']['status']=='RESEARCH_GRADED' for i in report['assets'].values()),
        'watch_valid':sum(i['watch_score']['status']=='RESEARCH_WATCH_VALID' for i in report['assets'].values()),
        'research_events':len(report['watch_events']),'signals':0}
    return report
