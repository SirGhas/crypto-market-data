"""Paired point-in-time benchmark: baseline vs strictly gated multi-factor model."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from causal_sma_backtest import run_backtest

def compare(candles, cutoff, factors=None, fast=5, slow=20, horizon=4, fee_bps=10):
    baseline=run_backtest(candles,cutoff,fast=fast,slow=slow,horizon=horizon,fee_bps=fee_bps)
    result={"mode":"PAIRED_HISTORICAL_PAPER_AUDIT","execution_allowed":False,
            "cutoff_utc":cutoff.astimezone(timezone.utc).isoformat(),
            "baseline":baseline,
            "multifactor":{"status":"NOT_EVALUABLE","signal":"NO_SIGNAL",
                           "reason":"NO_VERIFIED_POINT_IN_TIME_FACTORS"}}
    if not factors:
        return result
    required=("trend","momentum","volume","macro")
    if any(key not in factors for key in required):
        result["multifactor"]["reason"]="MISSING_REQUIRED_FACTOR"
        return result
    scores=[]
    for key in required:
        factor=factors[key]
        try:
            observed=datetime.fromisoformat(factor["observed_at_utc"])
            value=Decimal(str(factor["score"]))
        except (KeyError,TypeError,ValueError,InvalidOperation):
            result["multifactor"]["reason"]="INVALID_FACTOR"
            return result
        if observed.tzinfo is None or observed.astimezone(timezone.utc)>cutoff.astimezone(timezone.utc):
            result["multifactor"]["reason"]="FUTURE_OR_UNDATED_FACTOR"
            return result
        if not factor.get("source_verified") or not value.is_finite() or not Decimal(-1)<=value<=Decimal(1):
            result["multifactor"]["reason"]="UNVERIFIED_FACTOR"
            return result
        scores.append(value)
    aggregate=sum(scores)/Decimal(len(scores))
    signal="BUY_PAPER" if aggregate>=Decimal("0.5") else "SELL_PAPER" if aggregate<=Decimal("-0.5") else "NO_SIGNAL"
    result["multifactor"]={"status":"SCORED_PAPER_ONLY","signal":signal,
                           "equal_weight_score":str(aggregate),"execution_allowed":False,
                           "reason":"PREDECLARED_EQUAL_WEIGHT_EXPERIMENT"}
    return result
