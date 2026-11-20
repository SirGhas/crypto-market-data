"""Causal SMA crossover backtest; research baseline, never live trading."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

def run_backtest(candles, cutoff, fast=5, slow=20, horizon=4, fee_bps=10):
    if cutoff.tzinfo is None:
        raise ValueError("AWARE_CUTOFF_REQUIRED")
    if not (isinstance(fast, int) and isinstance(slow, int) and 1 < fast < slow):
        raise ValueError("INVALID_WINDOWS")
    if not isinstance(horizon, int) or horizon < 1:
        raise ValueError("INVALID_HORIZON")
    parsed = []
    for item in candles:
        try:
            t = datetime.fromisoformat(item["closed_at_utc"])
            p = Decimal(str(item["close"]))
        except (KeyError, ValueError, TypeError, InvalidOperation) as exc:
            raise ValueError("INVALID_CANDLE") from exc
        if t.tzinfo is None or not p.is_finite() or p <= 0:
            raise ValueError("INVALID_CANDLE")
        parsed.append((t.astimezone(timezone.utc), p))
    parsed.sort()
    if len(set(t for t, _ in parsed)) != len(parsed):
        raise ValueError("DUPLICATE_TIMESTAMP")
    cutoff_utc = cutoff.astimezone(timezone.utc)
    past = [(t,p) for t,p in parsed if t <= cutoff_utc]
    future = [(t,p) for t,p in parsed if t > cutoff_utc]
    out = {"mode":"HISTORICAL_PAPER_ONLY","execution_allowed":False,
           "cutoff_utc":cutoff_utc.isoformat(),"past_candles":len(past),
           "future_candles_hidden_at_decision":len(future),
           "strategy":"SMA_CROSSOVER_BASELINE","signal":"NO_SIGNAL",
           "reason":None,"evaluated":False}
    if len(past) < slow+1:
        out["reason"]="INSUFFICIENT_PRE_CUTOFF_HISTORY"
        return out
    def avg(prices, n):
        return sum(prices[-n:])/Decimal(n)
    previous=[p for _,p in past[:-1]]
    current=[p for _,p in past]
    a,b=avg(previous,fast),avg(previous,slow)
    c,d=avg(current,fast),avg(current,slow)
    if a <= b and c > d:
        out["signal"]="BUY_PAPER"
    elif a >= b and c < d:
        out["signal"]="SELL_PAPER"
    else:
        out["reason"]="NO_CROSSOVER_AT_CUTOFF"
        return out
    out["entry_price"]=str(current[-1])
    if len(future) < horizon:
        out["reason"]="INSUFFICIENT_POST_CUTOFF_HISTORY"
        return out
    try:
        fee=Decimal(str(fee_bps))
    except (InvalidOperation,TypeError,ValueError) as exc:
        raise ValueError("INVALID_FEE") from exc
    if not fee.is_finite() or fee<0:
        raise ValueError("INVALID_FEE")
    mark=future[horizon-1][1]
    direction=Decimal(1) if out["signal"]=="BUY_PAPER" else Decimal(-1)
    gross=direction*(mark-current[-1])/current[-1]
    net=gross-fee/Decimal(10000)
    out.update({"evaluated":True,"exit_price":str(mark),
                "exit_at_utc":future[horizon-1][0].isoformat(),
                "gross_return_pct":str(gross*100),"net_return_pct":str(net*100),
                "outcome":"WIN" if net>0 else "LOSS" if net<0 else "FLAT",
                "fee_bps":str(fee)})
    return out
