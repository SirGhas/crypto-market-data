"""Read-only, timestamped OKX order-book sweep for a hypothetical market buy.

The exchange depth is *observable liquidity*, not guaranteed execution.
No trading, authentication, order placement or trading authorization.
"""
import json
import time
import urllib.parse
import urllib.request
from decimal import Decimal as D, InvalidOperation

VERSION='alpha-1.6.5-depth-sweep-research'
NOTIONAL_USDT=D('1000')
MAX_BOOK_AGE_MS=5000
MAX_BOOK_TICKER_GAP_MS=15000
FEE_BUY_ASSUMPTION=D('0.001')
FEE_SELL_ASSUMPTION=D('0.001')
EXIT_SLIPPAGE_ASSUMPTION=D('0.001')

def num(v):
    try:
        x=D(str(v))
        return x if x.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None

def fmt(v):
    return format(v.quantize(D('0.00000001')).normalize(),'f')

def fetch_book(asset,transport=None,now_ms=None):
    url='https://www.okx.com/api/v5/market/books?'+urllib.parse.urlencode({'instId':asset+'-USDT','sz':'400'})
    if transport is None:
        req=urllib.request.Request(url,headers={'User-Agent':'alpha-v165-book-depth-research/1.0'})
        with urllib.request.urlopen(req,timeout=18) as response:
            payload=json.load(response)
    else:
        payload=transport(url)
    if not isinstance(payload,dict) or payload.get('code')!='0' or len(payload.get('data',[]))!=1:
        raise ValueError('BOOK_API_INVALID')
    book=payload['data'][0]
    ts=int(book.get('ts') or 0)
    observed=int(time.time()*1000) if now_ms is None else int(now_ms)
    if ts<=0 or ts>observed+3000 or observed-ts>MAX_BOOK_AGE_MS:
        raise ValueError('BOOK_STALE_OR_FUTURE')
    bids,asks=book.get('bids',[]),book.get('asks',[])
    if not bids or not asks:raise ValueError('EMPTY_DEPTH')
    def validate(items,descending):
        parsed=[]
        for row in items:
            if not isinstance(row,list) or len(row)<2:raise ValueError('INVALID_BOOK_ROW')
            p,q=num(row[0]),num(row[1])
            if p is None or q is None or p<=0 or q<0:raise ValueError('INVALID_BOOK_NUMBER')
            parsed.append((p,q))
        if any((x[0]<=y[0] if descending else x[0]>=y[0]) for x,y in zip(parsed,parsed[1:])):
            raise ValueError('BOOK_LEVEL_ORDER_INVALID')
        return parsed
    bids=validate(bids,True);asks=validate(asks,False)
    if bids[0][0]>=asks[0][0]:raise ValueError('BOOK_CROSSED')
    return {'status':'OBSERVED','symbol':asset+'-USDT','exchange_timestamp_ms':ts,
            'observed_timestamp_ms':observed,
            'age_ms':observed-ts,'best_bid':fmt(bids[0][0]),'best_ask':fmt(asks[0][0]),
            'ask_levels':[[fmt(p),fmt(q)] for p,q in asks],
            'ask_level_count':len(asks),
            'depth_scope':'OKX_PUBLIC_TOP_UP_TO_400_LEVELS',
            'not_historical_reconstruction':True}

def sweep(ask_levels,notional=NOTIONAL_USDT):
    amount=num(notional)
    if amount is None or amount<=0:raise ValueError('INVALID_NOTIONAL')
    remainder=amount;qty=D(0);cost=D(0);used=0;last=None
    for item in ask_levels:
        if not isinstance(item,(list,tuple)) or len(item)<2:raise ValueError('INVALID_ASK_LEVEL')
        price,size=num(item[0]),num(item[1])
        if price is None or size is None or price<=0 or size<0:raise ValueError('INVALID_DEPTH_VALUES')
        if last is not None and price<=last:raise ValueError('ASKS_NOT_ASCENDING')
        last=price
        if size==0:continue
        available=price*size
        take=min(remainder,available)
        qty+=take/price
        cost+=take
        remainder-=take
        used+=1
        if remainder<=D('0.00000000001'):break
    if qty<=0 or remainder> D('0.00000000001'):
        return {'status':'INSUFFICIENT_OBSERVED_DEPTH',
                'requested_notional_usdt':fmt(amount),'unfilled_notional_usdt':fmt(remainder),
                'vwap':None,'filled_base_quantity':None,'levels_consumed':used}
    return {'status':'FULLY_COVERED_BY_OBSERVED_ASK_DEPTH',
            'requested_notional_usdt':fmt(amount),'unfilled_notional_usdt':'0',
            'vwap':fmt(cost/qty),'filled_base_quantity':fmt(qty),'levels_consumed':used}

def evaluate(asset,market,book,notional=NOTIONAL_USDT):
    out={'asset':asset,'status':'BLOCKED_DEPTH_RESEARCH','notional_usdt':fmt(notional),
         'depth_sweep':None,'observed_book_timestamp_ms':book.get('exchange_timestamp_ms'),
         'observed_book_age_ms':book.get('age_ms'),
         'hypothetical_market_buy_vwap':None,'vwap_vs_best_ask_bps':None,
         'net_rr_after_depth_and_assumed_costs':None,
         'cost_assumptions':{'buy_fee':str(FEE_BUY_ASSUMPTION),
             'sell_fee':str(FEE_SELL_ASSUMPTION),
             'hypothetical_exit_slippage':str(EXIT_SLIPPAGE_ASSUMPTION),
             'exchange_fee_tier_verified':False,'exit_liquidity_verified':False},
         'blocking_reasons':[],'research_only':True,'signals_authorized':False,
         'trade_authorized':False,'order_submitted':False}
    blockers=out['blocking_reasons']
    t=market.get('observed_spot_price_v163',{})
    r=market.get('risk_v15',{})
    gate=market.get('market_buy_v164',{})
    if book.get('status')!='OBSERVED' or book.get('symbol')!=asset+'-USDT':
        blockers.append('NO_VALID_DEPTH_SNAPSHOT');return out
    if t.get('status')!='OBSERVED' or t.get('symbol')!=asset+'-USDT':
        blockers.append('NO_VALID_TICKER');return out
    try:
        if abs(int(t['observed_timestamp_ms'])-int(book['observed_timestamp_ms']))>MAX_BOOK_TICKER_GAP_MS:
            blockers.append('TICKER_BOOK_TIME_GAP_TOO_LARGE');return out
    except (KeyError,TypeError,ValueError):
        blockers.append('MISSING_TIMESTAMPS');return out
    if num(book.get('age_ms')) is None or num(book.get('age_ms'))>MAX_BOOK_AGE_MS:
        blockers.append('BOOK_NOT_FRESH');return out
    ask=num(book.get('best_ask'));tick_ask=num(t.get('best_ask'))
    if ask is None or tick_ask is None or ask<=0 or tick_ask<=0:
        blockers.append('INVALID_BEST_ASK');return out
    if abs(ask-tick_ask)/tick_ask>D('0.01'):
        blockers.append('TICKER_BOOK_ASK_DISAGREEMENT_OVER_1PCT');return out
    try:
        sw=sweep(book['ask_levels'],notional)
    except (ValueError,KeyError,TypeError) as e:
        blockers.append(str(e)[:100]);return out
    out['depth_sweep']=sw
    if sw['status']!='FULLY_COVERED_BY_OBSERVED_ASK_DEPTH':
        blockers.append('INSUFFICIENT_DEPTH_FOR_REFERENCE_NOTIONAL');return out
    vwap=num(sw['vwap'])
    if vwap is None or vwap<ask:
        blockers.append('INVALID_SWEEP_VWAP');return out
    out['hypothetical_market_buy_vwap']=fmt(vwap)
    out['vwap_vs_best_ask_bps']=fmt((vwap/ask-D(1))*10000)
    stop=num(r.get('hypothetical_stop'))
    target=num(gate.get('nearest_resistance_above_ask'))
    if r.get('data_validation',{}).get('matched_report_candle_identities') is not True or stop is None:
        blockers.append('STRUCTURAL_STOP_NOT_VERIFIED');return out
    if target is None or not (D(0)<stop<vwap<target):
        blockers.append('INVALID_STOP_OR_OVERHEAD_RESISTANCE');return out
    paid=vwap*(D(1)+FEE_BUY_ASSUMPTION)
    stop_receive=stop*(D(1)-FEE_SELL_ASSUMPTION)*(D(1)-EXIT_SLIPPAGE_ASSUMPTION)
    target_receive=target*(D(1)-FEE_SELL_ASSUMPTION)*(D(1)-EXIT_SLIPPAGE_ASSUMPTION)
    loss=paid-stop_receive
    if loss<=0:
        blockers.append('INVALID_NET_LOSS');return out
    out['net_rr_after_depth_and_assumed_costs']=fmt((target_receive-paid)/loss)
    blockers+=['BOOK_DEPTH_IS_SNAPSHOT_NOT_EXECUTION_GUARANTEE',
               'EXIT_BOOK_DEPTH_NOT_MODELED','REAL_EXCHANGE_FEES_UNVERIFIED',
               'RESEARCH_ONLY_NO_TRADE_AUTHORIZATION']
    out['status']='DEPTH_SCENARIO_COMPUTED_NOT_EXECUTION_VALIDATED'
    return out

def overlay(report,books):
    from engine.alpha_swing_run_v162 import UNIVERSE
    if report.get('version')!='alpha-1.6.4-market-buy-research' or set(report.get('assets',{}))!=set(UNIVERSE):
        raise ValueError('INVALID_V164_BASELINE')
    result=dict(report)
    result['version']=VERSION
    result['market_buy_depth_v165']={}
    for asset in UNIVERSE:
        v=evaluate(asset,result['assets'][asset],books.get(asset,{'status':'UNAVAILABLE'}))
        result['market_buy_depth_v165'][asset]=v
        result['assets'][asset]['market_buy_depth_v165']=v
    result['totals']=dict(result.get('totals',{}),
        market_buy_depth_assets=len(UNIVERSE),
        depth_scenarios_computed=sum(v['status']=='DEPTH_SCENARIO_COMPUTED_NOT_EXECUTION_VALIDATED'
                                     for v in result['market_buy_depth_v165'].values()),
        trade_authorized=0,signals=0)
    result.update(signals=[],signals_enabled=False,trading_enabled=False,
                  trade_authorized=False,research_only=True,
                  release_6_0_0_approved=False,backtest_completed=False,
                  continuous_freshness_proven=False)
    return result
