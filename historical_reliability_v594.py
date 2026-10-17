"""v5.9.4 research-only historical audit and deterministic multi-run replay.
No changes to live scores, gates, lifecycle, delivery state, or orders.
"""
import argparse
import datetime as dt
import json
import math
from pathlib import Path

TARGETS=('AAVE','AVAX','LINK','SUI')
FRAMES={'1h':3600,'4h':14400}
REASON_PRIORITY={
 'missing_or_stale_market_data':0,'insufficient_historical_candles':0,
 'historical_candle_gap':0,'invalid_historical_candle':0,
 'original_gate_not_passed':1,'volume_4h_below_candidate_threshold':2,
 'volume_1h_below_candidate_threshold':3,'rr_below_3_or_unverified':4,
 'missing_validated_static_levels':5,'not_confirmed_positive_event':6,
 'duplicate_or_pending_event':7,'no_new_event':8}
LABELS={
 'missing_or_stale_market_data':'داده بازار موجود یا تازه نیست',
 'insufficient_historical_candles':'تعداد کندل‌های تاریخی کافی نیست',
 'historical_candle_gap':'بین کندل‌های تاریخی فاصله وجود دارد',
 'invalid_historical_candle':'کندل تاریخی نامعتبر است',
 'original_gate_not_passed':'مجوز انتشار موتور اصلی تأیید نشده',
 'volume_4h_below_candidate_threshold':'حجم نسبی چهار‌ساعته زیر حد آزمایشی است',
 'volume_1h_below_candidate_threshold':'حجم نسبی یک‌ساعته زیر حد آزمایشی است',
 'rr_below_3_or_unverified':'نسبت ریسک به بازده تأییدشده کمتر از ۳ یا ناموجود است',
 'missing_validated_static_levels':'حمایت یا مقاومت چندبرخوردی معتبر موجود نیست',
 'not_confirmed_positive_event':'رویداد مثبت با کندل بسته‌شده تأیید نشده',
 'duplicate_or_pending_event':'شناسه رویداد تکراری یا از قبل در صف است',
 'no_new_event':'رویداد جدید قابل بررسی وجود ندارد'}

def numeric(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
def reasons_view(codes,metrics=None):
    codes=sorted(set(codes),key=lambda c:(REASON_PRIORITY.get(c,99),c))
    return {'primary_rejection_reason':codes[0] if codes else None,
            'primary_reason_fa':LABELS.get(codes[0],codes[0]) if codes else None,
            'secondary_reasons':codes[1:], 'all_reasons':codes,
            'measurements':metrics or {},
            'recheck_when':'پس از دریافت کندل بسته‌شده جدید و بازاجرای تمام کنترل‌ها' if codes else None}

def candle_history(frame,seconds,minimum=45):
    if not isinstance(frame,dict) or frame.get('status')!='available':return None,'missing_or_stale_market_data'
    cs=frame.get('candles')
    if not isinstance(cs,list) or len(cs)<minimum:return None,'insufficient_historical_candles'
    cs=sorted(cs,key=lambda x:x.get('t',-1))
    try:
        if any(not all(numeric(c.get(k)) for k in ('t','o','h','l','c','v')) or c['l']<=0 or c['v']<0 or c['l']>min(c['o'],c['c']) or c['h']<max(c['o'],c['c']) for c in cs):return None,'invalid_historical_candle'
        if any(b['t']-a['t']!=seconds for a,b in zip(cs,cs[1:])):return None,'historical_candle_gap'
    except (TypeError,KeyError):return None,'invalid_historical_candle'
    return cs,None

def relative_volume_at(cs,i):
    if i<20:return None
    base=sum(c['v'] for c in cs[i-20:i])/20
    return cs[i]['v']/base if base>0 else None

def historical_volume_audit(market,threshold=1.3):
    """Historical volume-only filter audit; never calls this a signal backtest.
    Uses only the 20 preceding closed candles for each observation.
    """
    result={}
    for coin in TARGETS:
        frames=market.get('pairs',{}).get(coin+'USDT',{}).get('frames',{})
        by_tf={}
        for tf,sec in FRAMES.items():
            cs,err=candle_history(frames.get(tf,{}),sec)
            if err:
                by_tf[tf]={'status':'UNVERIFIED','reason':err};continue
            vals=[relative_volume_at(cs,i) for i in range(20,len(cs))]
            good=sum(v is not None and v>=threshold for v in vals)
            by_tf[tf]={'status':'HISTORICAL_VOLUME_AUDIT_ONLY','observations':len(vals),
                       'threshold':threshold,'passing_observations':good,
                       'passing_fraction':round(good/len(vals),4) if vals else None,
                       'latest_ratio':round(vals[-1],4) if vals[-1] is not None else None}
        result[coin]=by_tf
    return result

def replay_delivery(events, initial_pending=None, initial_delivered=None):
    """Deterministic dry-run of enqueue/repeat/recovery, with no network or file writes."""
    pending=set(initial_pending or []);delivered=set(initial_delivered or [])
    results=[]
    for event in events:
        eid=event.get('id') if isinstance(event,dict) else None
        eligible=isinstance(event,dict) and event.get('eligible') is True and event.get('confirmed') is True
        if not isinstance(eid,str) or not eid or not eligible:
            results.append({'id':eid,'status':'BLOCK','diagnostic':reasons_view(['not_confirmed_positive_event'])});continue
        if eid in pending or eid in delivered:
            results.append({'id':eid,'status':'DUPLICATE_SUPPRESSED','diagnostic':reasons_view(['duplicate_or_pending_event'])});continue
        pending.add(eid)
        results.append({'id':eid,'status':'DRY_RUN_QUEUED','diagnostic':reasons_view([])})
    return {'results':results,'pending_ids':sorted(pending),'delivered_ids':sorted(delivered),'sent':0,'acknowledged':0}

def evaluate(market,dual,guard,lifecycle,outbox,now):
    stamp=dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat()
    docs={'market':market,'dual':dual,'guard':guard,'lifecycle':lifecycle}
    stale=[]
    for name,doc in docs.items():
        try:age=now-dt.datetime.fromisoformat(doc['generated_at_utc'].replace('Z','+00:00')).timestamp()
        except (TypeError,KeyError,ValueError,AttributeError):age=float('inf')
        if not 0<=age<=5400:stale.append(name)
    if stale:return {'schema_version':'5.9.4','status':'BLOCK','reasons':['stale_or_invalid_'+x for x in stale], 'release_6_0_0_approved':False}
    if not isinstance(outbox,dict) or not isinstance(outbox.get('pending'),dict) or not isinstance(outbox.get('delivered_ids'),list):
        return {'schema_version':'5.9.4','status':'BLOCK','reasons':['invalid_outbox'],'release_6_0_0_approved':False}
    if set(outbox['pending'])&set(outbox['delivered_ids']):
        return {'schema_version':'5.9.4','status':'BLOCK','reasons':['pending_delivered_collision'],'release_6_0_0_approved':False}
    ev={x.get('coin'):x for x in dual.get('evaluations',[]) if isinstance(x,dict)}
    diagnostics={}
    for coin in TARGETS:
        e=ev.get(coin,{})
        g=guard.get('coins',{}).get(coin,{})
        codes=[]; metrics={}
        if not e or e.get('score') is None:codes.append('missing_or_stale_market_data')
        if g.get('positive_publication_gate')!='PASS':codes.append('original_gate_not_passed')
        for tf in ('1h','4h'):
            v=e.get('relative_volume_'+tf)
            metrics['relative_volume_'+tf]={'actual':v,'candidate_minimum':1.3}
            if not numeric(v) or v<1.3:codes.append('volume_'+tf+'_below_candidate_threshold')
        rr=e.get('risk_reward_validated_levels')
        metrics['rr']={'actual':rr,'candidate_minimum':3}
        if not numeric(rr) or rr<3:codes.append('rr_below_3_or_unverified')
        levels=e.get('static_levels') or {}
        if not isinstance(levels,dict) or not all(numeric(levels.get(k)) for k in ('support','resistance')) or not levels['support']<levels['resistance'] or min(levels.get('support_touches',0),levels.get('resistance_touches',0))<2:
            codes.append('missing_validated_static_levels')
        diagnostics[coin]={'status':'BLOCK' if codes else 'CONDITIONAL_CHECKS_PASS','score':e.get('score'),'original_gate':g.get('positive_publication_gate'),**reasons_view(codes,metrics)}
    pending=outbox['pending'];delivered=outbox['delivered_ids']
    events=lifecycle.get('new_publishable_events',[])
    if not isinstance(events,list):events=[]
    replay_input=[]
    for x in events:
        if not isinstance(x,dict):continue
        coin=x.get('coin')
        confirmed=x.get('event_type') in ('4h_closed_breakout','4h_support_reclaim') and x.get('status')=='technical_event_needs_context' and x.get('volume_confirmed_4h') is True and x.get('lower_tf_confirmed') is True
        replay_input.append({'id':x.get('id'),'eligible':diagnostics.get(coin,{}).get('status')=='CONDITIONAL_CHECKS_PASS','confirmed':confirmed})
    first=replay_delivery(replay_input,pending,delivered)
    second=replay_delivery(replay_input,first['pending_ids'],first['delivered_ids'])
    recovery={'first_run_new_queued':sum(x['status']=='DRY_RUN_QUEUED' for x in first['results']),
              'replay_new_queued':sum(x['status']=='DRY_RUN_QUEUED' for x in second['results']),
              'duplicates_suppressed_on_replay':sum(x['status']=='DUPLICATE_SUPPRESSED' for x in second['results']),
              'persisted_pending_preserved':set(first['pending_ids'])==set(second['pending_ids']),
              'network_transport_used':False}
    return {'schema_version':'5.9.4','generated_at_utc':stamp,'status':'PASS_RESEARCH_ONLY',
            'coins':diagnostics,'historical_volume':historical_volume_audit(market),
            'event_replay':recovery,'outbox_existing_pending':len(pending),
            'summary':{'coins_blocked':sum(v['status']=='BLOCK' for v in diagnostics.values()),
                       'new_dry_run_events':recovery['first_run_new_queued'],'sent':0,'acknowledged':0,
                       'live_scores_modified':0,'publication_gates_modified':0},
            'release_6_0_0_approved':False,
            'limitations':['Historical volume frequency audit is NOT a predictive backtest or win-rate estimate',
                           'Available ~233 candle window cannot establish robust strategy performance',
                           'No historical entry/exit simulation, fees, slippage or walk-forward evaluation yet',
                           'Replay is deterministic in-memory simulation, not multi-hour live uptime',
                           'Volume threshold 1.3x remains experimental; no production rule changes']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data-dir',default='data');args=ap.parse_args()
    root=Path(args.data_dir)
    def load(p):return json.loads((root/p).read_text(encoding='utf-8'))
    now=dt.datetime.now(dt.timezone.utc).timestamp()
    r=evaluate(load('multisource_market.json'),load('dual_screen_v53.json'),load('unified_guard_v548.json'),load('event_lifecycle_v549.json'),load('delivery_outbox_state_v550.json'),now)
    (root/'historical_reliability_v594.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(r,ensure_ascii=False,indent=2))
    if r['status']=='BLOCK':raise SystemExit(1)
if __name__=='__main__':main()
