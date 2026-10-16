import datetime as dt
import json
import time
import urllib.request
from pathlib import Path

COINS = ['BTC','ETH','BNB','SOL','LTC','LINK','XRP','AVAX','SUI','AAVE']
FRAMES = {'5m':5,'15m':15,'1h':60,'4h':240}
BASE = 'https://api.kraken.com/0/public/OHLC'

def request(pair, interval):
    url = f'{BASE}?pair={pair}&interval={interval}'
    req = urllib.request.Request(url, headers={'User-Agent':'MarketResearchBot/1.1'})
    with urllib.request.urlopen(req, timeout=20) as response:
        data = json.load(response)
    if data.get('error'):
        raise ValueError(str(data['error']))
    key = next(k for k in data['result'] if k != 'last')
    return [{'t':int(r[0]),'o':float(r[1]),'h':float(r[2]),'l':float(r[3]),'c':float(r[4]),'v':float(r[6])} for r in data['result'][key][:-1][-300:]]

def indicators(rows):
    if len(rows)<234:
        return {'valid':False,'reason':'insufficient_closed_candles'}
    close=[x['c'] for x in rows]
    vol=[x['v'] for x in rows]
    avg=sum(vol[-21:-1])/20
    return {'valid':True,'close':close[-1],'last_candle_start_utc':rows[-1]['t'],'sma233':sum(close[-233:])/233,'relative_volume20':vol[-1]/avg if avg else None,'prior20_high':max(x['h'] for x in rows[-21:-1]),'prior20_low':min(x['l'] for x in rows[-21:-1])}

def main():
    out={'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'source':'Kraken public OHLC','forming_candle_excluded':True,'dominance':{'BTC.D':{'status':'unavailable','reason':'No verified historical dominance OHLCV provider configured'},'USDT.D':{'status':'unavailable','reason':'No verified historical dominance OHLCV provider configured'}},'markets':{},'summary':{}}
    ok=0
    for coin in COINS:
        out['markets'][coin]={}
        for quote in (['USD'] if coin=='BTC' else ['USD','XBT']):
            for tf,mins in FRAMES.items():
                pair=('XBT' if coin=='BTC' else coin)+quote
                name=('BTC/USD' if coin=='BTC' else coin+'/'+('BTC' if quote=='XBT' else 'USD'))
                out['markets'][coin].setdefault(name,{})
                try:
                    rows=request(pair,mins)
                    out['markets'][coin][name][tf]={'pair':pair,'candles':rows,'indicators':indicators(rows)}
                    ok+=1
                except Exception as e:
                    out['markets'][coin][name][tf]={'pair':pair,'error':str(e)}
                time.sleep(.35)
    out['summary']={'successful_feeds':ok,'attempted_feeds':76}
    if ok==0:
        raise RuntimeError('No successful market feeds; refusing to publish')
    Path('data').mkdir(exist_ok=True)
    Path('data/market.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(json.dumps(out['summary']))
if __name__=='__main__':main()
