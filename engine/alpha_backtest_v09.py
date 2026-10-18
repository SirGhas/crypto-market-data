"""Causal OHLC-only research backtest: fixed 3R, next-open fill, stop-first tie rule."""
from decimal import Decimal
from engine.alpha_core import BARS
FEE=Decimal('0.001') # illustrative per-side taker fee, verify actual account tiers
SLIP=Decimal('0.0005') # illustrative adverse per-side slippage
MIN_RVOL=Decimal('1.5')
HORIZON=12


def assess_exit(side, entry, stop, target, candles):
    """Stop-first for ambiguous intrabar fills. Return terminal raw fill and label."""
    for i, c in enumerate(candles, 1):
        # gap-through-stop is filled at worse opening price, never ideal stop
        if side == 'LONG':
            if c['open'] <= stop: return c['open'], 'GAP_STOP', i
            if c['open'] >= target: return target, 'GAP_TARGET_CAPPED', i
            if c['low'] <= stop: return stop, 'STOP', i
            if c['high'] >= target: return target, 'TARGET', i
        else:
            if c['open'] >= stop: return c['open'], 'GAP_STOP', i
            if c['open'] <= target: return target, 'GAP_TARGET_CAPPED', i
            if c['high'] >= stop: return stop, 'STOP', i
            if c['low'] <= target: return target, 'TARGET', i
    return candles[-1]['close'], 'TIMEOUT', len(candles)


def simulate(rows, timeframe, now_epoch, include_hypothetical_shorts=False):
    """All decisions use <= event candle; fill only at next candle's open."""
    period=BARS[timeframe][0]
    last=(now_epoch//period-1)*period
    times=[last-i*period for i in range(399)][::-1]
    if any(t not in rows for t in times):
        return {'status':'BLOCKED','reason':'MISSING_399_CONTIGUOUS_CLOSED_CANDLES','trades':[]}
    cs=[rows[t] for t in times]
    if any(not all(k in x for k in ('open','high','low','close','base_volume')) or
           min(x['open'],x['high'],x['low'],x['close'])<=0 or x['base_volume']<0 for x in cs):
        return {'status':'BLOCKED','reason':'INVALID_CANDLE','trades':[]}
    trades=[]; i=234
    while i+HORIZON<len(cs):
        candle=cs[i]
        prior=cs[i-20:i]
        avg=sum((x['base_volume'] for x in prior),Decimal(0))/20
        if avg<=0: i+=1;continue
        rvol=candle['base_volume']/avg
        break_up=candle['close']>max(x['high'] for x in prior)
        break_dn=candle['close']<min(x['low'] for x in prior)
        if not (break_up or (break_dn and include_hypothetical_shorts)) or rvol<MIN_RVOL:
            i+=1;continue
        side='LONG' if break_up else 'SHORT'
        sma233=sum((x['close'] for x in cs[i-232:i+1]),Decimal(0))/233
        previous_sma=sum((x['close'] for x in cs[i-233:i]),Decimal(0))/233
        if side=='LONG' and not(candle['close']>sma233 and sma233>previous_sma):i+=1;continue
        if side=='SHORT' and not(candle['close']<sma233 and sma233<previous_sma):i+=1;continue
        # Realized fill at next open, with adverse friction; stop from prior 20 closed bars.
        raw_open=cs[i+1]['open']
        entry=raw_open*(1+SLIP if side=='LONG' else 1-SLIP)
        stop=min(x['low'] for x in prior) if side=='LONG' else max(x['high'] for x in prior)
        risk=entry-stop if side=='LONG' else stop-entry
        if risk<=0: i+=1;continue
        target=entry+3*risk if side=='LONG' else entry-3*risk
        if target<=0:i+=1;continue
        raw_exit,reason,held=assess_exit(side,entry,stop,target,cs[i+1:i+1+HORIZON])
        exit_price=raw_exit*(1-SLIP if side=='LONG' else 1+SLIP)
        net_move=(exit_price-entry if side=='LONG' else entry-exit_price)
        # Fees charged on both actual notional legs, normalized by initial price for net R.
        fees=(entry+exit_price)*FEE
        net_r=(net_move-fees)/risk
        trades.append({'event_candle_id':f'{times[i]}:{period//60}', 'side':side,
            'entry_candle_id':f'{times[i+1]}:{period//60}', 'entry':str(entry),
            'stop':str(stop),'target':str(target),'initial_rr':'3',
            'exit':str(exit_price),'exit_reason':reason,'holding_candles':held,
            'rvol20':str(rvol),'sma233':str(sma233),'net_r_after_costs':str(net_r),
            'research_only':True,'signal_authorized':False})
        # Never allow any second position until first has actually exited.
        i+=held+1
    values=[Decimal(x['net_r_after_costs']) for x in trades]
    return {'status':'RESEARCH_BACKTEST_COMPUTED','trade_count':len(trades),
            'net_r_sum':str(sum(values,Decimal(0))),
            'mean_net_r':str(sum(values,Decimal(0))/len(values)) if values else None,
            'positive_fraction':str(sum(x>0 for x in values)/len(values)) if values else None,
            'assumed_fee_per_side':str(FEE),'assumed_adverse_slippage_per_side':str(SLIP),
            'risk_reward_target':3,'max_holding_candles':HORIZON,
            'spot_short_supported':False,'hypothetical_short_tested':include_hypothetical_shorts,
            'out_of_sample':False,'statistically_validated':False,
            'trades':trades,'signal_authorized':False}
