import datetime
import json
import time
import urllib.request
from pathlib import Path

PAIRS = {'BTC':'XBTUSD','ETH':'ETHUSD','BNB':'BNBUSD','SOL':'SOLUSD','LTC':'LTCUSD','LINK':'LINKUSD','XRP':'XRPUSD','AVAX':'AVAXUSD','SUI':'SUIUSD','AAVE':'AAVEUSD'}
INTERVALS = {'5m':5,'15m':15,'1h':60,'4h':240}

def fetch(pair, interval):
    url = f'https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}'
    req = urllib.request.Request(url, headers={'User-Agent':'PortfolioResearch/1.0'})
    with urllib.request.urlopen(req, timeout=20) as response:
        data = json.load(response)
    if data.get('error'):
        raise RuntimeError(str(data['error']))
    key = next(k for k in data['result'] if k != 'last')
    return [{'t':int(r[0]), 'o':float(r[1]), 'h':float(r[2]), 'l':float(r[3]), 'c':float(r[4]), 'v':float(r[6])} for r in data['result'][key][:-1][-300:]]

def indicators(rows):
    if len(rows) < 234:
        return {'valid':False, 'reason':'insufficient_closed_candles'}
    closes = [r['c'] for r in rows]
    vols = [r['v'] for r in rows]
    avg = sum(vols[-21:-1]) / 20
    return {'valid':True, 'close':closes[-1], 'last_candle_start_utc':rows[-1]['t'], 'sma233':sum(closes[-233:])/233, 'relative_volume20':vols[-1]/avg if avg else None, 'prior20_high':max(r['h'] for r in rows[-21:-1]), 'prior20_low':min(r['l'] for r in rows[-21:-1])}

def main():
    out = {'source':'Kraken public OHLC', 'quote':'USD, not Binance USDT', 'generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'forming_candle_excluded':True, 'markets':{}}
    successful = 0
    for symbol, pair in PAIRS.items():
        out['markets'][symbol] = {}
        for timeframe, interval in INTERVALS.items():
            try:
                rows = fetch(pair, interval)
                out['markets'][symbol][timeframe] = {'pair':pair, 'indicators':indicators(rows), 'candles':rows}
                successful += 1
            except Exception as exc:
                out['markets'][symbol][timeframe] = {'pair':pair, 'error':str(exc)}
            time.sleep(0.4)
    if successful == 0:
        raise RuntimeError('No markets could be retrieved; not publishing empty data')
    Path('data').mkdir(exist_ok=True)
    Path('data/market.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(f'Successful feeds: {successful}/40')

if __name__ == '__main__':
    main()
