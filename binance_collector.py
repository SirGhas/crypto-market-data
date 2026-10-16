"""Binance spot public REST data. Closed candles only. Stdlib Python 3.12."""
import datetime as dt, json, time, urllib.request
from pathlib import Path
COINS=['BTC','ETH','BNB','SOL','LTC','LINK','XRP','AVAX','SUI','AAVE']
FRAMES=['5m','15m','1h','4h']
BASE='https://api.binance.com/api/v3'
def get(path):
    req=urllib.request.Request(BASE+path,headers={'User-Agent':'market-research/5.0','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=12) as response: return json.load(response)
def main():
    now=int(time.time()*1000)
    output={'schema_version':5,'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'source':'Binance Spot REST API','quote':'USDT','status':'available','pairs':{},'errors':[]}
    try:
        ticker=get('/ticker/price')
        prices={v['symbol']:float(v['price']) for v in ticker}
    except Exception as e:
        prices={};output['errors'].append('ticker: '+str(e)[:180])
    for coin in COINS:
        for quote in (['USDT'] if coin=='BTC' else ['USDT','BTC']):
            sym=coin+quote
            obj={'symbol':sym,'last_trade_price':prices.get(sym),'last_trade_price_time_utc':output['generated_at_utc'] if sym in prices else None,'frames':{}}
            for frame in FRAMES:
                try:
                    raw=get(f'/klines?symbol={sym}&interval={frame}&limit=260')
                    candles=[{'start_ms':int(k[0]),'close_ms':int(k[6]),'open':float(k[1]),'high':float(k[2]),'low':float(k[3]),'close':float(k[4]),'volume':float(k[5])} for k in raw if int(k[6])<now]
                    obj['frames'][frame]={'candles':candles,'status':'available' if len(candles)>=234 else 'insufficient_history'}
                except Exception as e:
                    obj['frames'][frame]={'status':'unavailable','error':str(e)[:180]};output['errors'].append(f'{sym} {frame}: {str(e)[:90]}')
            output['pairs'][sym]=obj
    if not any(x['frames']['4h']['status']=='available' for x in output['pairs'].values()):output['status']='unavailable'
    elif output['errors']:output['status']='partial'
    Path('data').mkdir(exist_ok=True)
    Path('data/binance_market.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(json.dumps({'status':output['status'],'pairs':len(output['pairs']),'errors':len(output['errors'])}))
if __name__=='__main__':main()
