"""Research-only directional event overlay for Alpha v1.2 snapshots.

Do not call these signals. This module cannot authorize trades and uses closed candles.
"""
from decimal import Decimal as D
from hashlib import sha256
import json

VERSION='alpha-1.3-directional-research-alerts'
FLAGS={'research_only': True, 'signals_authorized': False, 'trade_authorized': False}
EARLY=('15m','30m','1h','2h')


def digest(value):
    return sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()[:24]


def classify(previous,current):
    """Preserve v1.2 scoring; attach independently gated research alerts.

    Previous may be 1.2 or 1.3. Only compare validated, non-regressing candles.
    """
    result=dict(current)
    result['version']=VERSION
    result['watch_events']=[]
    result['research_alerts']=[]
    result['alert_policy']={'minimum_early_delta':'10','positive_confirmation':'directional_positive_close_and_no_support_break',
        'downside_risk':'closed_15m_or_30m_support_break_with_rvol_ge_1.5',
        'requires_new_closed_candle':True,'mobile_notifications_enabled':False}
    cr=current.get('cross_run',{})
    if previous is None or cr.get('status')!='COMPARED' or cr.get('anomalies'):
        result['alert_status']='NO_VALID_COMPARABLE_BASELINE'
        result['totals']=dict(current.get('totals',{}), research_events=0)
        return result
    prev_seen=set(previous.get('alert_history',[]))
    # Keep bounded historical IDs to prevent repeat notifications beyond just the prior run.
    history=list(previous.get('alert_history',[]))[-2000:]
    per_asset_changes={}
    for asset,item in sorted(current.get('assets',{}).items()):
        old=previous.get('assets',{}).get(asset)
        if not old:continue
        timeframes=item.get('timeframes',{});old_tfs=old.get('timeframes',{})
        changed=[]
        for tf in (*EARLY,'4h','1D'):
            cur=timeframes.get(tf,{}) ; prior=old_tfs.get(tf,{})
            if cur.get('status')!='VALIDATED' or prior.get('status')!='VALIDATED':continue
            a=cur.get('last_closed_start_epoch');b=prior.get('last_closed_start_epoch')
            if isinstance(a,int) and isinstance(b,int) and a>b:changed.append(tf)
        if not changed:continue
        per_asset_changes[asset]=changed
        old_watch=old.get('watch_score',{});new_watch=item.get('watch_score',{})
        a=old_watch.get('early_score');b=new_watch.get('early_score')
        if a is not None and b is not None and any(t in changed for t in EARLY):
            delta=D(str(b))-D(str(a))
            if abs(delta)>=10:
                relevant=[tf for tf in EARLY if tf in changed]
                # A stronger score does not prove bullish direction: demand directional evidence.
                favorable=any(timeframes[tf].get('candle_direction')=='UP' and not timeframes[tf].get('broke_support_20') for tf in relevant)
                kind='EARLY_STRENGTHENING' if delta>0 and favorable else ('EARLY_SCORE_UP_UNCONFIRMED' if delta>0 else 'EARLY_WEAKENING')
                event={'asset':asset,'type':kind,'delta':str(delta),'old':str(a),'new':str(b),
                       'direction':'POTENTIAL_UP' if kind=='EARLY_STRENGTHENING' else ('DOWN_OR_WEAKENING' if delta<0 else 'UNCONFIRMED'),
                       'closed_candle_ids':{tf:timeframes[tf]['identity'] for tf in relevant},**FLAGS}
                if kind!='EARLY_SCORE_UP_UNCONFIRMED':_append(result,event,prev_seen,history)
        # Risk is independent of watch score; treat bearish high volume as risk, not opportunity.
        for tf in ('15m','30m'):
            if tf not in changed:continue
            candle=timeframes[tf]
            if candle.get('broke_support_20') and candle.get('candle_direction')=='DOWN' and D(str(candle.get('rvol20','0')))>=D('1.5'):
                event={'asset':asset,'type':'DOWNSIDE_SUPPORT_BREAK','direction':'RISK_DOWN','timeframe':tf,
                       'rvol20':str(candle['rvol20']),'close':str(candle['close']),
                       'closed_candle_ids':{tf:candle['identity']},**FLAGS}
                _append(result,event,prev_seen,history)
        old_tier=old.get('reference_score',{}).get('tier');new_tier=item.get('reference_score',{}).get('tier')
        if '4h' in changed and old_tier!=new_tier and old_tier and new_tier:
            event={'asset':asset,'type':'REFERENCE_TIER_CHANGE','direction':'REFERENCE_REEVALUATE',
                   'old_tier':old_tier,'new_tier':new_tier,'closed_candle_ids':{'4h':timeframes['4h']['identity']},**FLAGS}
            _append(result,event,prev_seen,history)
    result['alert_history']=history[-2000:]
    result['alert_status']='COMPARED_AND_CLASSIFIED'
    result['totals']=dict(current.get('totals',{}),research_events=len(result['research_alerts']),
                           risk_events=sum(e['direction']=='RISK_DOWN' for e in result['research_alerts']))
    return result


def _append(result,event,seen,history):
    key=digest({k:v for k,v in event.items() if k not in FLAGS})
    if key in seen:return
    event['event_id']=key
    result['research_alerts'].append(event)
    result['watch_events'].append(event)
    history.append(key);seen.add(key)
