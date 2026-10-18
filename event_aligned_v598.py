"""v5.9.8: event-aligned historical audit + restart-safe dry outbox. No orders or transport."""
import argparse, datetime as dt, json, math, os, tempfile
from pathlib import Path
COINS=('ETH','BNB','SOL','LTC','LINK','XRP','AVAX','SUI','AAVE','ZEC')
def candle_history(frame,seconds,minimum=233):
    if not isinstance(frame,dict) or frame.get('status')!='available':return None,'missing_feed'
    cs=frame.get('candles')
    if not isinstance(cs,list) or len(cs)<minimum:return None,'insufficient_history'
    try:
        cs=sorted(cs,key=lambda c:c['t'])
        if any(not all(isinstance(c.get(k),(int,float)) and math.isfinite(c[k]) for k in ('t','o','h','l','c','v')) or c['l']<=0 or c['v']<0 or c['l']>min(c['o'],c['c']) or c['h']<max(c['o'],c['c']) for c in cs):return None,'invalid_candles'
        if any(b['t']-a['t']!=seconds for a,b in zip(cs,cs[1:])):return None,'candle_gaps'
    except (KeyError,TypeError):return None,'invalid_candles'
    return cs,None
def relative_volume_at(cs,i):
    if i<20:return None
    avg=sum(c['v'] for c in cs[i-20:i])/20
    return cs[i]['v']/avg if avg>0 else None

THRESHOLDS=(1.0,1.1,1.2,1.3)

def audit_pair(market,coin):
    frames=market.get('pairs',{}).get(coin+'USDT',{}).get('frames',{})
    c4,e4=candle_history(frames.get('4h',{}),14400,233)
    c1,e1=candle_history(frames.get('1h',{}),3600,233)
    if e4 or e1:return {'status':'UNVERIFIED','reasons':[x for x in (e4,e1) if x]}
    by_end={c['t']+3600:i for i,c in enumerate(c1)}
    result={str(t):{'breakout':0,'reclaim':0,'both_volume_pass':0,'volume_pass_by_type':{'breakout':0,'reclaim':0}} for t in THRESHOLDS}
    events=[]
    for i in range(20,len(c4)):
        bar=c4[i]; prior=c4[i-20:i]; upper=max(x['h'] for x in prior);lower=min(x['l'] for x in prior)
        typ='breakout' if bar['c']>upper and bar['o']<=upper else ('reclaim' if bar['l']<lower and bar['c']>lower else None)
        if typ is None:continue
        end=bar['t']+14400
        j=by_end.get(end)
        if j is None or j<20:continue
        r4=relative_volume_at(c4,i);r1=relative_volume_at(c1,j)
        if r4 is None or r1 is None:continue
        event={'candle_end_utc':dt.datetime.fromtimestamp(end,dt.timezone.utc).isoformat(),'type':typ,'volume_4h':round(r4,4),'volume_1h':round(r1,4)}
        events.append(event)
        for t in THRESHOLDS:
            cell=result[str(t)];cell[typ]+=1
            if r4>=t and r1>=t:
                cell['both_volume_pass']+=1;cell['volume_pass_by_type'][typ]+=1
    return {'status':'AUDIT_ONLY','aligned_events':len(events),'thresholds':result,'recent_events':events[-12:],
            'limitations':['Only 4h closed breakout/reclaim pattern proxies; no trade entry/exit or win rate',
                           'Only closed 1h candles ending at same 4h boundary; no forward information',
                           'Limited retained candle history; zero events means insufficient evidence, not poor strategy']}

def atomic_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.tmp-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def replay_file(path,events,fail_before_write=False):
    """Durable dry-run only: never marks delivered or makes network calls."""
    path=Path(path)
    state=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'pending':{},'delivered_ids':[]}
    pending=state.get('pending');delivered=state.get('delivered_ids')
    if not isinstance(pending,dict) or not isinstance(delivered,list) or set(pending)&set(delivered):
        raise ValueError('invalid_or_colliding_outbox')
    accepted=0;duplicates=0;blocked=0
    for e in events:
        if not isinstance(e,dict) or not isinstance(e.get('id'),str) or not e['id'] or e.get('eligible') is not True or e.get('confirmed') is not True:
            blocked+=1;continue
        eid=e['id']
        if eid in pending or eid in delivered:duplicates+=1;continue
        pending[eid]={'status':'PENDING_DRY_RUN','event':e};accepted+=1
    if fail_before_write:raise OSError('injected_disk_failure_before_commit')
    atomic_json(path,{'pending':pending,'delivered_ids':delivered})
    return {'accepted':accepted,'duplicates':duplicates,'blocked':blocked,'pending':len(pending),'sent':0,'acknowledged':0}

def restart_simulation():
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/'outbox.json'
        good={'id':'synthetic:confirmed:1','eligible':True,'confirmed':True}
        bad={'id':'synthetic:forming:2','eligible':True,'confirmed':False}
        first=replay_file(path,[good,bad]);before=path.read_bytes()
        try:replay_file(path,[{'id':'synthetic:confirmed:3','eligible':True,'confirmed':True}],True)
        except OSError:pass
        unchanged=path.read_bytes()==before
        second=replay_file(path,[good,bad])
        third=replay_file(path,[{'id':'synthetic:confirmed:3','eligible':True,'confirmed':True}])
        checks={'confirmed_persisted':first['accepted']==1,'forming_blocked':first['blocked']==1,
                'injected_failure_no_partial_commit':unchanged,'duplicate_after_reload':second['duplicates']==1,
                'pending_survives_restart':third['pending']==2,'no_transport':all(x['sent']==x['acknowledged']==0 for x in (first,second,third))}
        return {'status':'PASS_DRY_RESTART' if all(checks.values()) else 'BLOCK','checks':checks,
                'limitations':['Local filesystem restart simulation, not GitHub Actions multi-hour uptime',
                               'No real network outage or delivery acknowledgement tested']}

def evaluate(market,now):
    try:age=now-dt.datetime.fromisoformat(market['generated_at_utc'].replace('Z','+00:00')).timestamp()
    except (KeyError,TypeError,ValueError):age=float('inf')
    if not 0<=age<=5400:return {'status':'BLOCK','reasons':['stale_or_invalid_market'],'release_6_0_0_approved':False}
    coins={coin:audit_pair(market,coin) for coin in COINS}
    restart=restart_simulation()
    return {'schema_version':'5.9.8','generated_at_utc':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),
            'status':'PASS_RESEARCH_ONLY' if restart['status']=='PASS_DRY_RESTART' else 'BLOCK',
            'coins':coins,'restart_replay':restart,
            'summary':{'coins_evaluated':len(coins),'unverified':sum(v['status']=='UNVERIFIED' for v in coins.values()),
                       'aligned_events':sum(v.get('aligned_events',0) for v in coins.values()),'sent':0,'acknowledged':0,
                       'live_scores_modified':0,'publication_gates_modified':0},
            'release_6_0_0_approved':False,
            'limitations':['Not a historical profitability backtest; no P&L, fees, slippage, walk-forward or win rate',
                           'Thresholds remain experimental and are not changed in production',
                           'Dry restart simulation only; no notification transport or live process restart tested']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--market',default='data/multisource_market.json');p.add_argument('--output',default='data/event_aligned_v598.json');a=p.parse_args()
    market=json.loads(Path(a.market).read_text(encoding='utf-8'))
    report=evaluate(market,dt.datetime.now(dt.timezone.utc).timestamp())
    atomic_json(a.output,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report['status']=='BLOCK':raise SystemExit(1)
if __name__=='__main__':main()
