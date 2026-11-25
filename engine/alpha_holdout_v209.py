"""Alpha 2.0.9: chronological holdout diagnostics for structural levels."""
from collections import Counter
from engine.alpha_score_audit_v180 import evaluate as replay

def summarize(events):
    result = {}
    for band in ("LOW", "MEDIUM", "HIGH"):
        rows = [e for e in events if e["score_band"] == band]
        counts = Counter(e["outcome"] for e in rows)
        resolved = counts["CONFIRMED_REJECTION"] + counts["CONFIRMED_CLOSE_THROUGH"]
        result[band] = {"observations": len(rows), "decision_windows": len({e["decision_epoch"] for e in rows}),
                        "outcomes": dict(counts), "resolved": resolved,
                        "rejection_fraction": counts["CONFIRMED_REJECTION"]/resolved if resolved else None}
    return result

def evaluate(bars):
    # Fixed split before evaluation; discard windows crossing the split.
    split = len(bars)*7//10
    boundary = bars[split][0]
    events = replay(bars)["events"]
    earlier = [e for e in events if e["decision_epoch"] + 12*14400 <= boundary]
    later = [e for e in events if e["decision_epoch"] >= boundary]
    return {"version":"alpha-2.0.9", "split_epoch":boundary,
            "earlier":summarize(earlier), "holdout":summarize(later),
            "excluded_cross_boundary":len(events)-len(earlier)-len(later),
            "research_only":True, "signals_enabled":False, "trading_enabled":False,
            "trade_authorized":False, "backtest_completed":False,
            "limitations":["DESCRIPTIVE_NOT_PROSPECTIVE","CORRELATED_LEVEL_OBSERVATIONS","BTC_4H_ONLY","NO_EXECUTION_BACKTEST"]}
