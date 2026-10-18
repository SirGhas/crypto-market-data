"""Causal, research-only spot swing setup: 4h primary, daily context, lower-TF watch."""
from decimal import Decimal as D
from engine.alpha_sma_v04 import sma_audit
from engine.alpha_momentum_v06 import rsi_wilder,volume_price_action
from engine.alpha_core import BARS

LOOKBACKS=(20,60,120,233)

def inspect(rows,tf,now):
    period=BARS[tf][0];last=(now//period-1)*period
    if any(last-i*period not in rows for i in range(234)):
        return {'status':'BLOCKED','reason':'MISSING_234_CLOSED_CONTIGUOUS_CANDLES'}
    s=sma_audit(rows,tf,now);r=rsi_wilder(rows,tf,now);v=volume_price_action(rows,tf,now)
    if (s['status'],r['status'],v['status'])!=('SMA_CLOSE_VALIDATED','RSI_WILDER_CLOSE_VALIDATED','NATIVE_VOLUME_PRICE_ACTION_VALIDATED'):
        return {'status':'BLOCKED','reason':'INDICATOR_INVALID'}
    identity=s['identity']
    if identity!=r['identity'] or identity!=v['identity']:
        return {'status':'BLOCKED','reason':'CANDLE_ID_MISMATCH'}
    previous={str(w):{'support':str(min(rows[last-i*period]['low'] for i in range(1,w+1))),
                      'resistance':str(max(rows[last-i*period]['high'] for i in range(1,w+1)))} for w in LOOKBACKS}
    c=rows[last];sma=s['smas'];rsi=D(r['value']);rvol=D(v['rvol20'])
    distance=lambda x:str((c['close']/D(x)-1)*100)
    return {'status':'VALIDATED','identity':identity,'last_closed_start_epoch':last,
            'close':str(c['close']),'rsi14':str(rsi),'rsi14_previous':r['previous'],
            'rvol20':str(rvol),'candle_direction':v['candle_direction'],
            'sma_close':sma,'trend_structure':s['trend_structure'],
            'static_levels':previous,
            'broke_resistance_20':c['close']>D(previous['20']['resistance']),
            'broke_support_20':c['close']<D(previous['20']['support']),
            'pct_from_sma233':distance(sma['SMA233']['value']),
            'native_volume_only':True,'signals_authorized':False}

def score_setup(primary,daily,early1,early2):
    blocked={'status':'BLOCKED','score':None,'parts':{},'explanations':[],'signals_authorized':False}
    if primary.get('status')!='VALIDATED' or daily.get('status')!='VALIDATED':
        return {**blocked,'reason':'PRIMARY_OR_DAILY_DATA_MISSING'}
    p=D(primary['close']); a=D(primary['sma_close']['SMA233']['value']);r=D(primary['rsi14']);v=D(primary['rvol20'])
    longtrend=p>a and primary['sma_close']['SMA233']['slope']=='UP'
    resistance=D(primary['static_levels']['20']['resistance']);support=D(primary['static_levels']['20']['support'])
    # Scores describe analytic conditions, not probabilities; score can be 60-79 pre-breakout.
    structure=30 if primary['broke_resistance_20'] else 20 if p>support and p>=resistance*D('.985') else 12 if p>support else 0
    volume=30 if v>=2 else 24 if v>=D('1.5') else 16 if v>=1 else 7 if v>=D('.7') else 0
    trend=20 if longtrend else 12 if p>a else 0
    momentum=10 if D('50')<=r<=D('70') else 6 if D('45')<=r<D('50') or D('70')<r<=D('75') else 0
    d=D(daily['close']); ds=D(daily['sma_close']['SMA233']['value']);daily_confirmed=d>ds and daily['sma_close']['SMA233']['slope']=='UP'
    higher=10 if daily_confirmed else 5 if d>ds else 0
    parts={'static_levels':structure,'native_volume':volume,'sma233':trend,'rsi14':momentum,'daily_confirmation':higher}
    score=sum(parts.values());tier='GREEN' if score>=80 else 'BLUE' if score>=70 else 'YELLOW' if score>=60 else 'GRAY'
    explanations=[f'4H: price vs SMA233={"above" if p>a else "below"}, SMA233 slope={primary["sma_close"]["SMA233"]["slope"]}',
                  f'4H: RVOL20={v}, RSI14={r}',
                  f'4H: close above 20-bar resistance={primary["broke_resistance_20"]}',
                  f'1D: price above SMA233={d>ds}, slope={daily["sma_close"]["SMA233"]["slope"]}']
    if primary['broke_support_20'] or not longtrend or not daily_confirmed:
        risk_state='CAUTION'
    else:risk_state='NEEDS_STRUCTURAL_STOP_AND_LIQUIDITY_CHECK'
    return {'status':'RESEARCH_GRADED','score':score,'tier':tier,'parts':parts,'explanations':explanations,
            'risk_state':risk_state,'breakout_confirmed':primary['broke_resistance_20'],
            'daily_trend_confirmed':daily_confirmed,'timeframe':'4h',
            'blocking_reasons':['NO_VALIDATED_STRUCTURAL_STOP','NO_LIQUIDITY_SPREAD_CHECK','NO_TRADE_RR_VALIDATION','RESEARCH_ONLY'],
            'signals_authorized':False}

def early_warning(one,two,main):
    if one.get('status')!='VALIDATED' or two.get('status')!='VALIDATED' or main.get('status')!='VALIDATED':
        return {'status':'BLOCKED','score':None,'signals_authorized':False}
    s1=one['sma_close']['SMA233'];s2=two['sma_close']['SMA233'];
    tests={'1h_above_sma233':s1['close_above'], '2h_above_sma233':s2['close_above'],
           '1h_sma233_rising':s1['slope']=='UP','2h_sma233_rising':s2['slope']=='UP',
           '1h_rsi_above_50':D(one['rsi14'])>50,'2h_rsi_above_50':D(two['rsi14'])>50,
           '1h_rvol_ge_1':D(one['rvol20'])>=1,'2h_rvol_ge_1':D(two['rvol20'])>=1,
           '1h_breakout':one['broke_resistance_20'],'2h_breakout':two['broke_resistance_20']}
    score=sum(10 for val in tests.values() if val)
    return {'status':'EARLY_WATCH_ONLY','score':score,'components':tests,
            'independent_of_4h_score':True,'not_a_buy_signal':True,
            'signals_authorized':False}

def build_report(markets,now,previous=None):
    result={'version':'alpha-1.1-swing-watch','research_only':True,'trading_enabled':False,
            'signals_enabled':False,'release_6_0_0_approved':False,'signals':[],
            'continuous_freshness_proven':False,'backtest_completed':False,
            'primary_timeframe':'4h','context_timeframe':'1D','early_timeframes':['1h','2h'],
            'run_epoch':now,'assets':{},'notifications':[],
            'explanation':'Scores are weighted condition coverage, NOT success probability or trade authorization'}
    assets=sorted({coin for tf in markets.values() for coin in tf})
    for coin in assets:
        audits={tf:markets.get(tf,{}).get(coin,{'status':'BLOCKED','reason':'MISSING'}) for tf in ('1h','2h','4h','1D')}
        main=score_setup(audits['4h'],audits['1D'],audits['1h'],audits['2h'])
        early=early_warning(audits['1h'],audits['2h'],audits['4h'])
        item={'timeframes':audits,'reference_score':main,'early_score':early,'trade_authorized':False}
        result['assets'][coin]=item
        before=(previous or {}).get('assets',{}).get(coin,{})
        prior_main=before.get('reference_score',{});prior_early=before.get('early_score',{})
        prior_ids={tf:before.get('timeframes',{}).get(tf,{}).get('identity') for tf in ('1h','2h','4h','1D')}
        ids={tf:audits[tf].get('identity') for tf in ('1h','2h','4h','1D')}
        # Prevent repeat alerts: emit only on new relevant closed candle and score tier changes.
        for kind,new,old,tf in [('REFERENCE',main,prior_main,'4h'),('EARLY',early,prior_early,'2h')]:
            if not previous or not old or ids[tf]==prior_ids[tf]:continue
            new_value=new.get('tier') if kind=='REFERENCE' else (new.get('score',0)//10 if new.get('score') is not None else None)
            old_value=old.get('tier') if kind=='REFERENCE' else (old.get('score',0)//10 if old.get('score') is not None else None)
            if new_value!=old_value and new.get('score') is not None:
                result['notifications'].append({'asset':coin,'kind':kind,'previous':old_value,'current':new_value,
                                                'closed_candle_id':ids[tf],'research_only':True})
    result['totals']={'expected':len(assets),'reference_graded':sum(x['reference_score']['status']=='RESEARCH_GRADED' for x in result['assets'].values()),
                      'early_valid':sum(x['early_score']['status']=='EARLY_WATCH_ONLY' for x in result['assets'].values()),
                      'notifications':len(result['notifications']),'signals':0}
    return result
