"""Conservative mark-to-market evaluation for paper signals only."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

def evaluate_paper_event(event, mark_price, marked_at, fee_bps=10):
    if event.get("mode") != "PAPER_ONLY" or event.get("execution_allowed") is not False:
        raise ValueError("NOT_PAPER_EVENT")
    if event.get("decision") not in ("BUY_PAPER", "SELL_PAPER"):
        raise ValueError("NOT_DIRECTIONAL_PAPER_SIGNAL")
    if not isinstance(marked_at, datetime) or marked_at.tzinfo is None:
        raise ValueError("AWARE_MARK_TIME_REQUIRED")
    try:
        entry_time = datetime.fromisoformat(event["observed_at_utc"])
        entry = Decimal(str(event["reference_price"]))
        mark = Decimal(str(mark_price))
        fee = Decimal(str(fee_bps))
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError("INVALID_PAPER_MARK") from exc
    if entry_time.tzinfo is None or marked_at <= entry_time:
        raise ValueError("MARK_MUST_FOLLOW_SIGNAL")
    if not all(x.is_finite() for x in (entry, mark, fee)) or entry <= 0 or mark <= 0 or fee < 0:
        raise ValueError("INVALID_PAPER_MARK")
    direction = Decimal(1) if event["decision"] == "BUY_PAPER" else Decimal(-1)
    gross = direction * (mark - entry) / entry
    net = gross - fee / Decimal(10000)
    return {"event_id": event["event_id"], "asset": event["asset"],
            "mode": "PAPER_ONLY", "execution_allowed": False,
            "marked_at_utc": marked_at.astimezone(timezone.utc).isoformat(),
            "gross_return_pct": str(gross * 100),
            "net_return_pct": str(net * 100),
            "fee_bps": str(fee),
            "outcome": "WIN" if net > 0 else "LOSS" if net < 0 else "FLAT"}
