"""Read-only paper signal gate: no order placement, no investment recommendation."""
from datetime import datetime, timedelta, timezone

def evaluate(feed, now_utc, max_age_minutes=30):
    """Return a traceable paper-only decision, fail closed on stale or unapproved inputs."""
    out = {"mode": "PAPER_ONLY", "signal": "NO_SIGNAL", "execution_allowed": False,
           "reasons": [], "timestamp_utc": now_utc.isoformat(),
           "timestamp_tehran": now_utc.astimezone(timezone(timedelta(hours=3, minutes=30))).isoformat()}
    if feed.get("status") == "BLOCKED":
        out["reasons"].append("FEED_BLOCKED")
    if not feed.get("analysis_enabled", False):
        out["reasons"].append("ANALYSIS_NOT_APPROVED")
    if not feed.get("reference_parity_approved", False):
        out["reasons"].append("REFERENCE_PARITY_PENDING")
    if not feed.get("liquidity_approved", False):
        out["reasons"].append("LIQUIDITY_PENDING")
    frame = feed.get("frames", {}).get("15m", {})
    stamp = frame.get("last_closed_at_utc")
    try:
        candle_time = datetime.fromisoformat(stamp)
        if candle_time.tzinfo is None or not timedelta(0) <= now_utc - candle_time <= timedelta(minutes=max_age_minutes):
            out["reasons"].append("STALE_OR_FUTURE_CANDLE")
    except (TypeError, ValueError):
        out["reasons"].append("MISSING_OR_INVALID_CANDLE_TIME")
    if not out["reasons"]:
        out["signal"] = "ELIGIBLE_FOR_PAPER_STRATEGY"
    return out
