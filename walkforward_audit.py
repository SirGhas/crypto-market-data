"""Predeclared daily walk-forward audit; independent paper events, not a portfolio."""
from datetime import datetime, date, time, timedelta, timezone
from decimal import Decimal
from causal_sma_backtest import run_backtest

def audit_window(candles,start_day,end_day,fast=5,slow=20,horizon=4,fee_bps=10):
    if isinstance(start_day,str):
        start_day=date.fromisoformat(start_day)
    if isinstance(end_day,str):
        end_day=date.fromisoformat(end_day)
    if start_day>end_day:
        raise ValueError("INVALID_DATE_WINDOW")
    days=(end_day-start_day).days+1
    if days>366:
        raise ValueError("WINDOW_TOO_LARGE")
    events=[]
    for n in range(days):
        day=start_day+timedelta(days=n)
        cutoff=datetime.combine(day+timedelta(days=1),time.min,tzinfo=timezone.utc)
        result=run_backtest(candles,cutoff,fast=fast,slow=slow,horizon=horizon,fee_bps=fee_bps)
        events.append({"day_utc":day.isoformat(),"signal":result["signal"],
                       "evaluated":result["evaluated"],"reason":result["reason"],
                       "outcome":result.get("outcome"),
                       "net_return_pct":result.get("net_return_pct")})
    signals=[e for e in events if e["signal"]!="NO_SIGNAL"]
    evaluated=[e for e in signals if e["evaluated"]]
    returns=[Decimal(e["net_return_pct"]) for e in evaluated]
    return {"mode":"PREDECLARED_WALK_FORWARD_PAPER_EVENTS","execution_allowed":False,
            "start_day_utc":start_day.isoformat(),"end_day_utc":end_day.isoformat(),
            "strategy":"SMA_CROSSOVER_BASELINE","fast":fast,"slow":slow,
            "horizon_days":horizon,"fee_bps":fee_bps,
            "trading_assumptions":"Same-close hypothetical entry; fees single deduction; overlapping event outcomes possible; NOT executable portfolio returns",
            "days_checked":days,"no_signal_days":sum(e["signal"]=="NO_SIGNAL" for e in events),
            "signal_days":len(signals),"evaluated_signals":len(evaluated),
            "pending_signals":len(signals)-len(evaluated),
            "wins":sum(e["outcome"]=="WIN" for e in evaluated),
            "losses":sum(e["outcome"]=="LOSS" for e in evaluated),
            "flats":sum(e["outcome"]=="FLAT" for e in evaluated),
            "mean_event_net_return_pct":str(sum(returns)/len(returns)) if returns else None,
            "events":events}
