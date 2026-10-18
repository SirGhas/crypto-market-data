"""Alpha 0.4: close-only SMA and paginated OKX closed-candle history. Research only."""
import json
import time
import urllib.parse
import urllib.request
from decimal import Decimal
from engine.alpha_core import BARS, COINS, InvalidMarketData, parse_okx_rows, relative_close
from engine.alpha_diagnostics import diagnose

WINDOWS = (20, 50, 233)
TARGET_CLOSED = 300   # 233 SMA + 1 slope point; more history, NOT 300 trade backtests
MAX_PAGES = 5
ENDPOINT = 'https://www.okx.com/api/v5/market/history-candles'


def fetch_page(inst, bar, after=None):
    params = {'instId':inst, 'bar':bar, 'limit':'100'}
    if after is not None:
        params['after'] = str(after)
    url = ENDPOINT + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'Accept':'application/json','User-Agent':'research-alpha/0.4'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status != 200:
            raise InvalidMarketData('HTTP_NOT_OK')
        payload=json.loads(resp.read(2_000_000))
    if str(payload.get('code')) != '0' or not isinstance(payload.get('data'),list):
        raise InvalidMarketData('OKX_API_ERROR')
    return payload


def collect_history(inst, tf, now, page_fetch=fetch_page):
    period, bar = BARS[tf]
    merged={}; after=None; previous_oldest=None
    for page in range(MAX_PAGES):
        payload=page_fetch(inst,bar,after)
        raw=payload['data']
        if not raw: break
        # OKX after means older records; use *oldest raw timestamp*, including unclosed rows.
        try: oldest=min(int(x[0]) for x in raw if isinstance(x,list) and x)
        except (ValueError,TypeError) as exc: raise InvalidMarketData('BAD_HISTORY_TIMESTAMP') from exc
        if previous_oldest is not None and oldest >= previous_oldest:
            raise InvalidMarketData('PAGINATION_NOT_ADVANCING')
        parsed=parse_okx_rows(payload,tf,now)
        for stamp, candle in parsed.items():
            if stamp in merged and merged[stamp] != candle:
                raise InvalidMarketData('OVERLAP_CONFLICT')
            merged[stamp]=candle
        previous_oldest=oldest
        after=oldest
        if len(merged)>=TARGET_CLOSED:break
        if len(raw)<100:break
    expected=(now//period-1)*period
    needed=[expected-i*period for i in range(234)]
    if any(t not in merged for t in needed):
        raise InvalidMarketData('SMA233_HISTORY_MISSING_OR_NOT_CONTIGUOUS')
    return merged


def sma_audit(rows, tf, now):
    period,_=BARS[tf]
    expected=(now//period-1)*period
    if any((expected-i*period) not in rows for i in range(234)):
        return {'status':'BLOCKED','reason':'NEED_234_CONSECUTIVE_CLOSED_CANDLES'}
    closes=[rows[expected-i*period]['close'] for i in range(234)]
    if any(not isinstance(x,Decimal) or not x.is_finite() or x<=0 for x in closes):
        return {'status':'BLOCKED','reason':'INVALID_CLOSE'}
    result={'status':'SMA_CLOSE_VALIDATED','identity':f'{expected}:{period//60}',
            'closed_history_count':len(rows),'sma_source':'CLOSE','smas':{},
            'signals_authorized':False}
    for n in WINDOWS:
        value=sum(closes[:n],Decimal(0))/Decimal(n)
        prior=sum(closes[1:n+1],Decimal(0))/Decimal(n)
        result['smas'][f'SMA{n}']={
            'value':str(value),'previous':str(prior),
            'slope':('UP' if value>prior else 'DOWN' if value<prior else 'FLAT'),
            'close_above':closes[0]>value,
            'close_below':closes[0]<value}
    result['trend_structure']='BULLISH_ALIGNMENT' if (result['smas']['SMA20']['value'] and
        Decimal(result['smas']['SMA20']['value'])>Decimal(result['smas']['SMA50']['value'])>Decimal(result['smas']['SMA233']['value'])) else 'BEARISH_ALIGNMENT' if (
        Decimal(result['smas']['SMA20']['value'])<Decimal(result['smas']['SMA50']['value'])<Decimal(result['smas']['SMA233']['value'])) else 'MIXED'
    return result


def evaluate(tf, now, asset_rows, btc_rows):
    period,_=BARS[tf]
    ratio=relative_close(asset_rows,btc_rows,tf,now)
    sma=sma_audit(asset_rows,tf,now)
    native=diagnose(asset_rows,tf,now,period)
    good=(ratio.get('status')=='VALIDATED_RELATIVE_CLOSE' and sma.get('status')=='SMA_CLOSE_VALIDATED'
          and native.get('status')=='RESEARCH_DIAGNOSTICS_ONLY'
          and ratio.get('identity')==sma.get('identity')==native.get('identity'))
    return {'status':'RESEARCH_VALIDATED' if good else 'BLOCKED',
            'relative_to_btc':ratio,'sma_close':sma,'native_diagnostics':native,
            'score':None,'tier':None,'validated_trade_rr':None,'signal_authorized':False}
