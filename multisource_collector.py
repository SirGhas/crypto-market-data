"""Public spot OHLCV: Bybit first, OKX fallback; no synthetic volume."""
import datetime as dt, json, time, urllib.request, urllib.parse
from pathlib import Path
COINS=('BTC','ETH','BNB','SOL','LTC','LINK','XRP','AVAX','SUI','AAVE')
FRAMES={'5m':(5,'5','5m'),'15m':(15,'15','15m'),'1h':(60,'60','1H'),'4h':(240,'240','4H')}
ROOT=Path('data'); ROOT.mkdir(exist_ok=True)

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'crypto-market-research/5.1','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=13) as res: return json.load(res)

def bybit(symbol,frame):
    interval=FRAMES[frame][1]
    q=urllib.parse.urlencode({'category':'spot','symbol':symbol,'interval':interval,'limit':260})
    d=get('https://api.bybit.com/v5/market/kline?'+q)
    if d.get('retCode')!=0: raise ValueError(str(d.get('retMsg')))
    return [{'t':int(a[0])//1000,'o':float(a[1]),'h':float(a[2]),'l':float(a[3]),'c':float(a[4]),'v':float(a[5])} for a in d['result']['list']]

def okx(symbol,frame):
    inst=symbol[:-4]+'-USDT' if symbol.endswith('USDT') else symbol[:-3]+'-BTC'
    bar=FRAMES[frame][2]
    # OKX history-candles returns at most 100 records per page; use 4 pages for SMA233.
    rows=[]; after=None
    for _ in range(4):
        args={'instId':inst,'bar':bar,'limit':'100'}
        if after is not None: args['after']=after
        d=get('https://www.okx.com/api/v5/market/history-candles?'+urllib.parse.urlencode(args))
        if d.get('code')!='0': raise ValueError(str(d.get('msg')))
        chunk=d.get('data',[])
        if not chunk: break
        rows.extend(chunk); after=chunk[-1][0]
        if len(rows)>=255: break
    return [{'t':int(a[0])//1000,'o':float(a[1]),'h':float(a[2]),'l':float(a[3]),'c':float(a[4]),'v':float(a[5]),'confirmed':a[8]=='1'} for a in rows]

def validate(rows,frame,now):
    seconds=FRAMES[frame][0]*60
    clean={}
    for a in rows:
        if a['t']+seconds>now-2 or a.get('confirmed',True) is False: continue
        if not (a['l']>0 and a['l']<=min(a['o'],a['c'])<=max(a['o'],a['c'])<=a['h'] and a['v']>=0): continue
        clean[a['t']]=a
    candles=[clean[k] for k in sorted(clean)]
    if len(candles)<233: raise ValueError('insufficient_closed_candles:'+str(len(candles)))
    if now-(candles[-1]['t']+seconds)>seconds+180: raise ValueError('stale_closed_candle')
    return candles[-250:]

def main():
    now=int(time.time()); output={'schema_version':51,'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(), 'quote':'USDT','kind':'spot_closed_candles','pairs':{},'summary':{}}
    for coin in COINS:
        for quote in (('USDT',) if coin=='BTC' else ('USDT','BTC')):
            symbol=coin+quote; entry={'frames':{}}
            for frame in FRAMES:
                failures=[]
                for source,fn in [('Bybit Spot',bybit),('OKX Spot',okx)]:
                    try:
                        candles=validate(fn(symbol,frame),frame,now)
                        entry['frames'][frame]={'status':'available','source':source,'last_closed_at_utc':dt.datetime.fromtimestamp(candles[-1]['t']+FRAMES[frame][0]*60,dt.timezone.utc).isoformat(),'candles':candles}
                        break
                    except Exception as exc:
                        failures.append(source+': '+str(exc)[:130])
                else: entry['frames'][frame]={'status':'unavailable','errors':failures}
            output['pairs'][symbol]=entry
    available=sum(f['status']=='available' for p in output['pairs'].values() for f in p['frames'].values())
    output['summary']={'available_feeds':available,'attempted_feeds':len(output['pairs'])*len(FRAMES),'status':'available' if available==len(output['pairs'])*len(FRAMES) else ('partial' if available else 'unavailable')}
    (ROOT/'multisource_market.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(json.dumps(output['summary']))
if __name__=='__main__': main()
