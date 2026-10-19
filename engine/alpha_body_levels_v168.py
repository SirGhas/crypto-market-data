"""BTC-only experimental closed-candle body-first / wick-aware S/R audit.
Research only; no trading authorization. Distinguish candidates from validated levels.
"""
from decimal import Decimal as D, InvalidOperation
from engine.alpha_resistance_v167 import closed_candles

TIMEFRAMES={'15m':('15m',900),'30m':('30m',1800),'1h':('1H',3600),
            '2h':('2H',7200),'4h':('4H',14400),'1D':('1Dutc',86400)}
WINDOW=100

def number(v):
    try:
        d=D(str(v));return d if d.is_finite() else None
    except (ValueError,TypeError,InvalidOperation):return None

def fmt(v):return format(v.quantize(D('.00000001')).normalize(),'f')

def parse(rows,tf,now):
    interval=TIMEFRAMES[tf][1]; out=[];seen=set()
    for r in rows:
        if len(r)<9 or str(r[8])!='1':continue
        t=int(r[0])//1000
        if t in seen:raise ValueError('DUPLICATE_CLOSED_CANDLE')
        seen.add(t)
        o,h,l,c,v=[number(r[i]) for i in (1,2,3,4,5)]
        if any(x is None for x in (o,h,l,c,v)) or min(o,h,l,c)<=0 or v<0 or h<max(o,c,l) or l>min(o,c,h):
            raise ValueError('INVALID_OHLCV')
        if t%interval or t+interval>now:raise ValueError('INVALID_CLOSED_CANDLE_TIME')
        out.append((t,o,h,l,c,v))
    out.sort()
    if len(out)<60 or any(b[0]-a[0]!=interval for a,b in zip(out,out[1:])):
        raise ValueError('GAPPED_HISTORY')
    return out

def extract(tf,bars):
    if len(bars)<60:raise ValueError('INSUFFICIENT_HISTORY')
    closes=[x[4] for x in bars]; last=closes[-1]
    tr=[]
    for i,b in enumerate(bars):
        prev=bars[i-1][4] if i else b[4]
        tr.append(max(b[2]-b[3],abs(b[2]-prev),abs(b[3]-prev)))
    atr=sum(tr[-14:])/D(14)
    tol=max(last*D('0.0005'),atr*D('0.15'))
    # Body extremes (not wicks) produce candidate pivot prices.
    cands=[]
    for i in range(2,len(bars)-2):
        b=bars[i];top=max(b[1],b[4]);bottom=min(b[1],b[4])
        above=all(top>max(bars[j][1],bars[j][4]) for j in (i-2,i-1,i+1,i+2))
        below=all(bottom<min(bars[j][1],bars[j][4]) for j in (i-2,i-1,i+1,i+2))
        if above:cands.append(('resistance',top,i))
        if below:cands.append(('support',bottom,i))
    output=[]
    for side in ('support','resistance'):
        points=sorted((p,i) for s,p,i in cands if s==side)
        groups=[]
        for p,i in points:
            if groups and p-groups[-1][-1][0]<=tol:groups[-1].append((p,i))
            else:groups.append([(p,i)])
        for group in groups:
            price=sum((p for p,i in group),D(0))/len(group)
            if (side=='resistance' and price<=last) or (side=='support' and price>=last):continue
            episodes=[];last_index=-100
            for i in range(1,len(bars)-2):
                prev=bars[i-1];b=bars[i]
                top=max(b[1],b[4]);bottom=min(b[1],b[4])
                if side=='resistance':
                    touched=prev[4]<price-tol and b[2]>=price-tol
                    rejected=b[4]<price and b[4]<b[1]
                    reaction=price-min(x[3] for x in bars[i+1:i+3])
                    confirmed=reaction>=atr*D('.3')
                    wick=max(D(0),b[2]-top)
                else:
                    touched=prev[4]>price+tol and b[3]<=price+tol
                    rejected=b[4]>price and b[4]>b[1]
                    reaction=max(x[2] for x in bars[i+1:i+3])-price
                    confirmed=reaction>=atr*D('.3')
                    wick=max(D(0),bottom-b[3])
                if touched and rejected and confirmed and i-last_index>=6:
                    avg=sum(x[5] for x in bars[i-20:i])/D(20) if i>=20 else None
                    episodes.append({'start_epoch':b[0],'response_atr':fmt(reaction/atr),
                        'wick_atr':fmt(wick/atr),'candle_rvol20':fmt(b[5]/avg) if avg and avg>0 else None,
                        'volume_is_trade_by_price':False})
                    last_index=i
            output.append({'type':side,'body_level':fmt(price),
                'zone_low':fmt(min(p for p,i in group)),'zone_high':fmt(max(p for p,i in group)),
                'body_pivot_count':len(group),'confirmed_approach_rejections':len(episodes),
                'events':episodes[-8:],'status':'CANDIDATE_EVIDENCE_RESEARCH',
                'is_verified_seller_or_buyer_flow':False})
    output.sort(key=lambda v:abs(number(v['body_level'])-last))
    return {'status':'BODY_LEVEL_RESEARCH','timeframe':tf,'last_closed_identity':str(bars[-1][0])+':'+str(TIMEFRAMES[tf][1]//60),
        'last_close':fmt(last),'atr14_simple_research':fmt(atr),
        'tolerance':fmt(tol),'nearest_support_candidate':next((v for v in output if v['type']=='support'),None),
        'nearest_resistance_candidate':next((v for v in output if v['type']=='resistance'),None),
        'candidates':output,'limitations':['100_RECENT_CANDLES_ONLY','PIVOT_BODY_EXTREMES_NOT_TRADE_FLOW',
           'WICKS_ARE_REJECTION_EVIDENCE_ONLY','REJECTION_EVENTS_NOT_DEDUPED_ACROSS_TIMEFRAMES',
           'CANDIDATES_NOT_BACKTESTED']}

def btc_probe(transport=None,now=None):
    import json,time,urllib.request,urllib.parse
    stamp=int(time.time()) if now is None else int(now)
    reports={}
    for tf,(bar,period) in TIMEFRAMES.items():
        url='https://www.okx.com/api/v5/market/candles?'+urllib.parse.urlencode(
             {'instId':'BTC-USDT','bar':bar,'limit':'100'})
        if transport:payload=transport(url)
        else:
            req=urllib.request.Request(url,headers={'User-Agent':'alpha-body-levels-v168/1.0'})
            with urllib.request.urlopen(req,timeout=18) as f:payload=json.load(f)
        if not isinstance(payload,dict) or payload.get('code')!='0':raise ValueError('EXCHANGE_RESPONSE_'+tf)
        reports[tf]=extract(tf,parse(payload['data'],tf,stamp))
    return {'version':'alpha-1.6.8-btc-body-wick-probe','asset':'BTC','quote':'USDT',
       'primary_timeframe':'4h','timeframes':reports,
       'primary_support':reports['4h']['nearest_support_candidate'],
       'primary_resistance':reports['4h']['nearest_resistance_candidate'],
       'research_only':True,'signals':[],'signals_enabled':False,
       'trading_enabled':False,'trade_authorized':False,'backtest_completed':False,
       'continuous_freshness_proven':False}
