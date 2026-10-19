"""Research-only spot ticker snapshot after Alpha 1.6.2 completes.

Tickers are observations at collection time, NOT prices at 4h candle close.
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from engine.alpha_swing_run_v162 import main as collect_v162, UNIVERSE

VERSION='alpha-1.6.3-observed-spot-prices'

def valid_positive(x):
    try:
        v=Decimal(str(x))
        return v if v.is_finite() and v>0 else None
    except (InvalidOperation,ValueError,TypeError):
        return None

def observed_ticker(asset, transport=None, now_ms=None):
    url='https://www.okx.com/api/v5/market/ticker?'+urllib.parse.urlencode({'instId':asset+'-USDT'})
    if transport is None:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'alpha-spot-snapshot-v163/1.0'}),timeout=18) as res:
            obj=json.load(res)
    else:
        obj=transport(url)
    if not isinstance(obj,dict) or obj.get('code')!='0' or not isinstance(obj.get('data'),list) or len(obj['data'])!=1:
        raise ValueError('INVALID_TICKER_RESPONSE')
    row=obj['data'][0]
    price=valid_positive(row.get('last'))
    bid=valid_positive(row.get('bidPx'))
    ask=valid_positive(row.get('askPx'))
    ts=int(row.get('ts') or 0)
    observed=int(time.time()*1000) if now_ms is None else int(now_ms)
    if row.get('instId')!=asset+'-USDT' or price is None or bid is None or ask is None or bid>ask:
        raise ValueError('INVALID_TICKER_PRICE_OR_SYMBOL')
    if ts<=0 or ts>observed+3000 or observed-ts>30000:
        raise ValueError('STALE_OR_FUTURE_TICKER')
    return {'status':'OBSERVED','symbol':asset+'-USDT','quote_currency':'USDT',
            'last_trade_price':str(price),'best_bid':str(bid),'best_ask':str(ask),
            'exchange_timestamp_ms':ts,'observed_timestamp_ms':observed,
            'observed_at_utc':datetime.fromtimestamp(observed/1000,timezone.utc).isoformat(),
            'source':'OKX_SPOT_TICKER','timestamp_age_ms':observed-ts,
            'not_closed_candle_price':True,'not_synchronized_across_assets':True}

def attach_prices(report, observations):
    if report.get('version')!='alpha-1.6.2-btc-benchmark-research' or set(report.get('assets',{}))!=set(UNIVERSE):
        raise ValueError('INVALID_V162_BASELINE')
    report=dict(report)
    report['version']=VERSION
    report['observed_spot_prices']={}
    for asset in UNIVERSE:
        value=observations.get(asset,{'status':'UNAVAILABLE','reason':'NO_TICKER_OBSERVATION'})
        report['observed_spot_prices'][asset]=value
        report['assets'][asset]['observed_spot_price_v163']=value
    report['totals']=dict(report.get('totals',{}),observed_spot_prices=sum(v['status']=='OBSERVED' for v in report['observed_spot_prices'].values()))
    report.update(signals=[],signals_enabled=False,trading_enabled=False,trade_authorized=False,
                  research_only=True,release_6_0_0_approved=False,backtest_completed=False)
    return report

def main():
    collect_v162()
    report=json.loads(Path('artifacts/alpha_swing_v162.json').read_text(encoding='utf-8'))
    observed={}
    for asset in UNIVERSE:
        try:observed[asset]=observed_ticker(asset)
        except Exception as exc:
            observed[asset]={'status':'UNAVAILABLE','reason':type(exc).__name__+':'+str(exc)[:110]}
        time.sleep(0.15)
    final=attach_prices(report,observed)
    p=Path('artifacts/alpha_swing_v163.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(final,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('ALPHA_V163',json.dumps({'assets':len(UNIVERSE),'observed_spot_prices':final['totals']['observed_spot_prices'],
                                   'signals':0,'trading_enabled':False}))

if __name__=='__main__': main()
