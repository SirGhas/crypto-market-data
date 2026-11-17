"""Historical point-in-time replay audit. Never claim profitability without dated candles."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

def replay_audit(candles, cutoff, min_history=20):
    if cutoff.tzinfo is None:
        raise ValueError("CUTOFF_MUST_BE_TIMEZONE_AWARE")
    parsed = []
    for candle in candles:
        try:
            stamp = datetime.fromisoformat(candle["closed_at_utc"])
            close = Decimal(str(candle["close"]))
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            raise ValueError("INVALID_HISTORICAL_CANDLE") from exc
        if stamp.tzinfo is None or not close.is_finite() or close <= 0:
            raise ValueError("INVALID_HISTORICAL_CANDLE")
        parsed.append((stamp.astimezone(timezone.utc), close))
    if len(set(t for t, _ in parsed)) != len(parsed):
        raise ValueError("DUPLICATE_HISTORICAL_TIMESTAMP")
    parsed.sort()
    before = [(t, p) for t, p in parsed if t <= cutoff.astimezone(timezone.utc)]
    future = [(t, p) for t, p in parsed if t > cutoff.astimezone(timezone.utc)]
    return {"mode": "HISTORICAL_AUDIT", "execution_allowed": False,
            "cutoff_utc": cutoff.astimezone(timezone.utc).isoformat(),
            "visible_candles": len(before), "hidden_future_candles": len(future),
            "ready_for_signal_evaluation": len(before) >= min_history,
            "status": "READY_FOR_STRATEGY" if len(before) >= min_history else "INSUFFICIENT_HISTORY",
            "visible_last_close": str(before[-1][1]) if before else None}
