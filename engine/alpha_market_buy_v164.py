"""Research-only market-buy evaluation; NEVER places or authorizes an order.

Uses a time-stamped observed ticker ASK as a one-unit reference, not an executable
VWAP. Fees/slippage are labeled user-configurable *assumptions*, not broker quotes.
"""
from copy import deepcopy
from decimal import Decimal as D, InvalidOperation
VERSION='alpha-1.6.4-market-buy-research'
UNIVERSE={'BTC','ETH','BNB','SOL','XRP','AAVE','AVAX','LINK','LTC','SUI','ZEC'}
NOTIONAL_USDT=D('1000')
BUY_FEE_RATE=D('0.001')
SELL_FEE_RATE=D('0.001')
SLIPPAGE_RATE_EACH_SIDE=D('0.001')
MAX_TICKER_BOOK_GAP_MS=15000

def dec(v):
    try:
        x=D(str(v));return x if x.is_finite() else None
    except (TypeError,ValueError,InvalidOperation):return None

def fmt(v):
    return format(v.quantize(D('0.00000001')).normalize(),'f')

def assess(asset, market, notional=NOTIONAL_USDT):
    result={'asset':asset,'status':'BLOCKED_MARKET_BUY_RESEARCH',
       'quote_currency':'USDT','research_only':True,'trade_authorized':False,
       'signals_authorized':False,'order_submitted':False,
       'reference_notional_usdt':str(notional),
       'observed_last_trade':None,'observed_best_ask':None,
       'observed_best_bid':None,'ticker_observed_at_utc':None,
       'estimated_entry_with_assumed_slippage':None,
       'hypothetical_stop':None,'nearest_resistance_above_ask':None,
       'gross_rr_from_ask':None,'scenario_net_rr_after_assumed_costs':None,
       'risk_per_unit_including_assumed_exit_cost':None,
       'reward_per_unit_after_assumed_exit_cost':None,
       'scenario_assumptions':{
           'buy_fee_rate':str(BUY_FEE_RATE),'sell_fee_rate':str(SELL_FEE_RATE),
           'slippage_rate_per_side':str(SLIPPAGE_RATE_EACH_SIDE),
           'notional_usdt':str(notional),'verified_exchange_fee_tier':False,
           'verified_order_size_depth':False,'verified_execution_vwap':False,
           'assumptions_are_not_verified_costs':True},
       'blocking_reasons':[]}
    reasons=result['blocking_reasons']
    tick=market.get('observed_spot_price_v163') or {}
    risk=market.get('risk_v15') or {}
    evidence=market.get('evidence_v161') or {}
    book=evidence.get('order_book') or {}
    ask=dec(tick.get('best_ask'));bid=dec(tick.get('best_bid'))
    last=dec(tick.get('last_trade_price'));stop=dec(risk.get('hypothetical_stop'))
    if tick.get('status')!='OBSERVED' or tick.get('symbol')!=asset+'-USDT' or not ask or not bid or bid>ask:
        reasons.append('NO_VALID_OBSERVED_SPOT_ASK_BID')
    else:
        result.update(observed_best_ask=fmt(ask),observed_best_bid=fmt(bid),
                      observed_last_trade=fmt(last) if last else None,
                      ticker_observed_at_utc=tick.get('observed_at_utc'))
    if risk.get('data_validation',{}).get('matched_report_candle_identities') is not True or not stop:
        reasons.append('UNVERIFIED_STRUCTURAL_STOP_AND_ATR')
    if notional<=0:reasons.append('INVALID_REFERENCE_NOTIONAL')
    if book.get('status')!='OBSERVED':
        reasons.append('ORDER_BOOK_NOT_VALIDATED')
    else:
        snaps=book.get('snapshots') or []
        t=dec(tick.get('observed_timestamp_ms'))
        if not t or not snaps:
            reasons.append('NO_COMPARABLE_TIMESTAMPED_BOOK')
        elif min(abs(int(t)-int(s.get('observed_timestamp_ms',0))) for s in snaps)>MAX_TICKER_BOOK_GAP_MS:
            reasons.append('TICKER_BOOK_TIME_GAP_TOO_LARGE')
    if ask and stop and not D(0)<stop<ask:
        reasons.append('STOP_NOT_BELOW_MARKET_ENTRY')
    resistance=dec(risk.get('nearest_overhead_resistance'))
    # Historical first resistance recorded relative to *closed candle* can be below ASK:
    # never silently use that stale notion of overhead. Re-evaluate at ASK using all raw levels.
    raw=market.get('resistance_gate_v151') or {}
    candidates=[dec(raw.get(k)) for k in ('first_four_hour_resistance','first_daily_resistance')]
    higher=sorted({v for v in candidates if v is not None and ask is not None and v>ask})
    if higher:
        resistance=higher[0]
    elif resistance is not None and ask is not None and resistance>ask:
        pass
    else:
        resistance=None
        reasons.append('NO_VERIFIED_RESISTANCE_ABOVE_OBSERVED_ASK')
    if resistance is not None:result['nearest_resistance_above_ask']=fmt(resistance)
    if ask and stop and D(0)<stop<ask and resistance:
        result['gross_rr_from_ask']=fmt((resistance-ask)/(ask-stop))
        entry=ask*(D(1)+SLIPPAGE_RATE_EACH_SIDE)
        buy_all_in=entry*(D(1)+BUY_FEE_RATE)
        stop_net=stop*(D(1)-SLIPPAGE_RATE_EACH_SIDE)*(D(1)-SELL_FEE_RATE)
        target_net=resistance*(D(1)-SLIPPAGE_RATE_EACH_SIDE)*(D(1)-SELL_FEE_RATE)
        loss=buy_all_in-stop_net
        reward=target_net-buy_all_in
        if loss>0:
            result['estimated_entry_with_assumed_slippage']=fmt(entry)
            result['hypothetical_stop']=fmt(stop)
            result['risk_per_unit_including_assumed_exit_cost']=fmt(loss)
            result['reward_per_unit_after_assumed_exit_cost']=fmt(reward)
            result['scenario_net_rr_after_assumed_costs']=fmt(reward/loss)
            if reward/loss<D(2):reasons.append('SCENARIO_NET_RR_BELOW_2')
        else:reasons.append('INVALID_RISK_SCENARIO')
    else:reasons.append('INSUFFICIENT_MARKET_RISK_INPUTS')
    reasons.extend(['ORDER_SIZE_VWAP_NOT_VERIFIED','EXCHANGE_FEE_TIER_NOT_VERIFIED',
                    'SLIPPAGE_MODEL_NOT_BACKTESTED','STRUCTURAL_LEVEL_QUALITY_NOT_FINAL',
                    'RESEARCH_ONLY_NO_TRADE_AUTHORIZATION'])
    if result['scenario_net_rr_after_assumed_costs'] is not None:
        result['status']='SCENARIO_COMPUTED_NOT_EXECUTION_VALIDATED'
    return result

def overlay(report):
    if report.get('version')!='alpha-1.6.3-observed-spot-prices' or set(report.get('assets',{}))!=UNIVERSE:
        raise ValueError('INVALID_V163_UNIVERSE')
    x=deepcopy(report);x['version']=VERSION
    x['market_buy_research']={a:assess(a,x['assets'][a]) for a in sorted(UNIVERSE)}
    for a,v in x['market_buy_research'].items():
        x['assets'][a]['market_buy_v164']=v
        x['assets'][a]['trade_authorized']=False
    x['totals']=dict(x.get('totals',{}),
        market_buy_assets=11,
        market_buy_scenarios_computed=sum(v['scenario_net_rr_after_assumed_costs'] is not None
                                          for v in x['market_buy_research'].values()),
        market_buy_execution_validated=0,trade_authorized=0,signals=0)
    x.update(signals=[],signals_enabled=False,trading_enabled=False,
             trade_authorized=False,research_only=True,release_6_0_0_approved=False,
             backtest_completed=False,continuous_freshness_proven=False)
    return x
