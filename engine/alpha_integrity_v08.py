"""Alpha 0.8 offline source-integrity and causal event study summary; no signals."""
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from statistics import median

PERIOD={'5m':300,'15m':900,'1h':3600,'4h':14400}
HORIZONS=('1','3','6','12')

def d(s):
    try:
        x=Decimal(str(s))
        if x.is_finite():return x
    except (TypeError,InvalidOperation,ValueError):pass
    raise ValueError('NONFINITE_METRIC')

def parse_time(s):return datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()

def check_reports(s,m):
    if s.get('source_version')!='alpha-0.6-rsi-volume' or m.get('version')!='alpha-0.6-rsi-volume':raise ValueError('SOURCE_VERSION_MISMATCH')
    if s.get('source_run_id')!=m.get('run_id') or s.get('source_time_utc')!=m.get('timestamp_utc'):raise ValueError('RUN_IDENTITY_MISMATCH')
    if not s.get('research_only') or not m.get('research_only') or s.get('signals_enabled') is not False or m.get('signals_enabled') is not False or s.get('trading_enabled') is not False or m.get('trading_enabled') is not False:raise ValueError('UNSAFE_INPUT')
    if m.get('totals',{}).get('validated')!=40 or s.get('totals',{}).get('graded')!=40:raise ValueError('INCOMPLETE_MARKETS')
    t=parse_time(m['timestamp_utc'])
    for tf,markets in m['timeframes'].items():
        if tf not in PERIOD:raise ValueError('UNRECOGNIZED_TF')
        expected=(int(t)//PERIOD[tf]-1)*PERIOD[tf]
        for asset,item in markets.items():
            ident=f'{expected}:{PERIOD[tf]//60}'
            if item['status']!='RESEARCH_VALIDATED' or any(item[k].get('identity')!=ident for k in ('sma_close','rsi14','native_volume_price_action')):
                raise ValueError('LATEST_BAR_IDENTITY_MISMATCH')
            scored=s['screens'][tf][asset]
            if scored.get('status')!='RESEARCH_GRADED' or scored.get('signal_authorized') is not False:raise ValueError('SCORING_STATUS_MISMATCH')
    return True

def compare_runs(previous,current):
    if not previous:return {'status':'NO_PREVIOUS_BASELINE','proof':False,'advanced':[],'unchanged_expected':[],'anomalies':[]}
    if previous.get('version')!='alpha-0.6-rsi-volume' or current.get('version')!='alpha-0.6-rsi-volume':raise ValueError('BAD_COMPARE_VERSIONS')
    old_run=previous.get('run_id');new_run=current.get('run_id')
    if not old_run or not new_run or str(old_run)==str(new_run):return {'status':'INVALID_RUN_PAIR','proof':False,'advanced':[],'unchanged_expected':[],'anomalies':['SAME_OR_MISSING_RUN_ID']}
    ptime=parse_time(previous['timestamp_utc']);ctime=parse_time(current['timestamp_utc'])
    if ctime<=ptime:return {'status':'INVALID_RUN_PAIR','proof':False,'advanced':[],'unchanged_expected':[],'anomalies':['NONINCREASING_RUN_TIME']}
    changed=[];unchanged=[];anomalies=[]
    for tf,markets in current['timeframes'].items():
        pblock=previous.get('timeframes',{}).get(tf,{})
        if set(markets)!=set(pblock):anomalies.append(f'{tf}:ASSET_SET_CHANGED');continue
        for asset,item in markets.items():
            before=pblock[asset];p=PERIOD[tf]
            i0=before['sma_close'].get('identity');i1=item['sma_close'].get('identity')
            try:old_id=int(i0.split(':')[0]);new_id=int(i1.split(':')[0])
            except (ValueError,AttributeError,IndexError):anomalies.append(f'{tf}/{asset}:BAD_ID');continue
            identifier=f'{tf}/{asset}'
            # For an unchanged closed bar, deterministic indicators must be identical.
            if new_id==old_id:
                fields=[('sma_close','smas'),('rsi14','value'),('native_volume_price_action','rvol20')]
                if any(before[x].get(y)!=item[x].get(y) for x,y in fields):anomalies.append(identifier+':CLOSED_BAR_REVISED')
                else:unchanged.append(identifier)
            elif new_id>old_id and (new_id-old_id)%p==0:changed.append(identifier)
            else:anomalies.append(identifier+':REGRESSED_OR_MISALIGNED_ID')
    # Two reports are evidence of an advancing feed, not continuously proven freshness.
    status='ANOMALY_DETECTED' if anomalies else 'ADVANCED_SAMPLE_CONFIRMED' if changed else 'NO_ADVANCE_YET'
    return {'status':status,'proof':False,'sample_checks_advanced':len(changed), 'sample_checks_unchanged':len(unchanged),
            'advanced':changed,'unchanged_expected':unchanged,'anomalies':anomalies,
            'note':'Two snapshots do not prove continuous freshness; unchanged 1h/4h before their bar closes is normal.'}

def event_statistics(m):
    results={};sum_input=0;sum_selected=0
    for tf,assets in m['timeframes'].items():
        results[tf]={}
        for asset,item in assets.items():
            raw=item['event_study']['events'];sum_input+=len(raw)
            # Each event's forward 12-bar window embargoes all subsequent events through that horizon.
            previous_selected_epoch=None; selected=[];invalid=0
            for ev in sorted(raw,key=lambda v:int(v['candle_id'].split(':')[0])):
                epoch=int(ev['candle_id'].split(':')[0]);side=ev['direction']
                if side not in ('breakout','breakdown'):invalid+=1;continue
                if previous_selected_epoch is not None and epoch<=previous_selected_epoch+12*PERIOD[tf]:continue
                if any(h not in ev.get('forward',{}) for h in HORIZONS):invalid+=1;continue
                selected.append(ev);previous_selected_epoch=epoch
            sum_selected+=len(selected)
            split={}
            for name,match in [('ALL',lambda e:True),('BREAKOUT',lambda e:e['direction']=='breakout'),('BREAKDOWN',lambda e:e['direction']=='breakdown'),('SMA233_ALIGNED',lambda e:(e.get('above_sma233') is True and e.get('sma233_slope')=='UP') if e['direction']=='breakout' else (e.get('above_sma233') is False and e.get('sma233_slope')=='DOWN'))]:
                group=[e for e in selected if match(e)]
                summary={}
                for h in HORIZONS:
                    vals=[d(e['forward'][h]['direction_aligned_pct']) for e in group]
                    summary[h]={'n':len(vals),'positive_count':sum(v>0 for v in vals),
                                'positive_fraction':str(Decimal(sum(v>0 for v in vals))/len(vals)) if vals else None,
                                'mean_direction_aligned_pct':str(sum(vals)/len(vals)) if vals else None,
                                'median_direction_aligned_pct':str(median(vals)) if vals else None}
                split[name]=summary
            results[tf][asset]={'events_reported':len(raw),'events_embargo_selected':len(selected),
                                'invalid_event_records':invalid,'horizon_embargo':12,'statistics':split}
    return {'events_reported':sum_input,'events_embargo_selected':sum_selected,'embargo_policy':'PER_ASSET_PER_TIMEFRAME_12_BAR_NO_OVERLAP',
            'limitations':['Same timestamp across assets can still be correlated','No fees, spread, slippage, entry/stop/target or trade PnL', 'Only 399 candles of local history; no out-of-sample test'],
            'markets':results}

def analyze(scoring,momentum,previous=None):
    check_reports(scoring,momentum)
    return {'version':'alpha-0.8-integrity-event-summary','source_run_id':momentum['run_id'],'source_time_utc':momentum['timestamp_utc'],
            'research_only':True,'signals_enabled':False,'trading_enabled':False,'release_6_0_0_approved':False,
            'signals':[],'continuous_freshness_proven':False,'backtest_completed':False,
            'source_integrity_verified':True,'cross_run':compare_runs(previous,momentum),
            'event_summary':event_statistics(momentum),'outcome':'RESEARCH_DIAGNOSTICS_ONLY'}
