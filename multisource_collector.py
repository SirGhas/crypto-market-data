"""Public spot OHLCV: OKX primary; controlled Gate.io BTC-pair fallback.
No Binance. No synthetic OHLCV. Existing Bybit fallback retained for other feeds.
"""
import datetime as dt, json, time, urllib.request, urllib.parse
from pathlib import Path
COINS=('BTC','ETH','BNB','SOL','LTC','LINK','XRP','AVAX','SUI','AAVE')
FRAMES={'5m':(5,'5','5m'),'15m':(15,'15','15m'),'1h':(60,'60','1H'),'4h':(240,'240','4H')}
GATE_APPROVED={'BNBBTC','XRPBTC','AAVEBTC','AVAXBTC','LINKBTC','SUIBTC'}
ROOT=Path('data'); ROOT.mkdir(exist_ok=True)

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'crypto-market-research/5.4.5','Accept':'application/json'})
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

def gate(symbol,frame):
    if symbol not in GATE_APPROVED:
        raise ValueError('gate_pair_not_approved')
    pair=symbol[:-3]+'_BTC'
    interval={'5m':'5m','15m':'15m','1h':'1h','4h':'4h'}[frame]
    q=urllib.parse.urlencode({'currency_pair':pair,'interval':interval,'limit':350})
    d=get('https://api.gateio.ws/api/v4/spot/candlesticks?'+q)
    if not isinstance(d,list): raise ValueError('unexpected_gate_response')
    # Gate spot: [timestamp, quote_volume, close, high, low, open, base_volume, ...]
    # v is BASE asset volume, same unit as OKX/Bybit spot volume for the pair.
    rows=[]
    for a in d:
        if not isinstance(a,list) or len(a)<7: raise ValueError('malformed_gate_candle')
        rows.append({'t':int(a[0]),'o':float(a[5]),'h':float(a[3]),'l':float(a[4]),'c':float(a[2]),'v':float(a[6])})
    return rows

def validate(rows,frame,now):
    seconds=FRAMES[frame][0]*60
    clean={}
    for a in rows:
        if a['t']+seconds>now-2 or a.get('confirmed',True) is False: continue
        if not (a['l']>0 and a['l']<=min(a['o'],a['c'])<=max(a['o'],a['c'])<=a['h'] and a['v']>=0): continue
        clean[a['t']]=a
    candles=[clean[k] for k in sorted(clean)]
    if len(candles)<233: raise ValueError('insufficient_closed_candles:'+str(len(candles)))
    if any(b['t']-a['t']!=seconds for a,b in zip(candles[-233:],candles[-232:])):
        raise ValueError('gap_in_last_233_candles')
    if now-(candles[-1]['t']+seconds)>seconds+180: raise ValueError('stale_closed_candle')
    return candles[-250:]

def main():
    now=int(time.time()); output={'schema_version':51,'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(), 'quote':'USDT','kind':'spot_closed_candles','pairs':{},'summary':{}}
    for coin in COINS:
        for quote in (('USDT',) if coin=='BTC' else ('USDT','BTC')):
            symbol=coin+quote; entry={'frames':{}}
            for frame in FRAMES:
                failures=[]
                # Never change the OKX-first rule. Gate is approved only for the six explicitly reviewed BTC pairs.
                providers=[('OKX Spot',okx)]
                if symbol in GATE_APPROVED:
                    providers.append(('Gate.io Spot',gate))
                else:
                    providers.append(('Bybit Spot',bybit))
                for source,fn in providers:
                    try:
                        candles=validate(fn(symbol,frame),frame,now)
                        feed={'status':'available','source':source,'last_closed_at_utc':dt.datetime.fromtimestamp(candles[-1]['t']+FRAMES[frame][0]*60,dt.timezone.utc).isoformat(),'candles':candles}
                        if source=='Gate.io Spot':
                            recent=candles[-233:]
                            nonzero=sum(c['v']>0 for c in recent)
                            feed['liquidity_caution']={'low_timeframe_volume_confirmation_required':frame in ('5m','15m'),'nonzero_volume_candles_last_233':nonzero,'total_candles':len(recent)}
                        entry['frames'][frame]=feed
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
