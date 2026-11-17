"""Deterministic, append-only paper evaluation records; no broker integration."""
import hashlib
import json
from datetime import datetime, timezone

def make_record(asset, strategy, gate, decision, price, observed_at):
    if not isinstance(observed_at, datetime) or observed_at.tzinfo is None:
        raise ValueError("AWARE_TIMESTAMP_REQUIRED")
    if decision not in ("NO_SIGNAL", "WATCH", "BUY_PAPER", "SELL_PAPER"):
        raise ValueError("INVALID_PAPER_DECISION")
    if decision in ("BUY_PAPER", "SELL_PAPER") and gate.get("signal") != "ELIGIBLE_FOR_PAPER_STRATEGY":
        raise ValueError("PAPER_GATE_NOT_APPROVED")
    if gate.get("execution_allowed") is not False:
        raise ValueError("EXECUTION_MUST_BE_DISABLED")
    if not isinstance(price, (int, float, str)):
        raise ValueError("INVALID_REFERENCE_PRICE")
    from decimal import Decimal, InvalidOperation
    try:
        px = Decimal(str(price))
    except InvalidOperation as exc:
        raise ValueError("INVALID_REFERENCE_PRICE") from exc
    if not px.is_finite() or px <= 0:
        raise ValueError("INVALID_REFERENCE_PRICE")
    payload = {"asset": asset, "strategy": strategy, "mode": "PAPER_ONLY",
               "decision": decision, "reference_price": str(px),
               "observed_at_utc": observed_at.astimezone(timezone.utc).isoformat(),
               "gate_reasons": list(gate.get("reasons", [])), "execution_allowed": False}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["event_id"] = hashlib.sha256(canonical.encode()).hexdigest()[:24]
    return payload

def append_unique(records, record):
    if any(existing["event_id"] == record["event_id"] for existing in records):
        return list(records)
    return [*records, record]
