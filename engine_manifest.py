"""Generate an auditable, read-only manifest for the current engine reports.

No market data is fetched; timestamps are report timestamps, not execution time.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = {
    "screen": "data/dual_screen_v53.json",
    "guard": "data/unified_guard_v548.json",
    "delivery": "data/delivery_health_v550.json",
}


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def build_manifest(root=ROOT):
    records = {}
    for name, relpath in FILES.items():
        raw = (root / relpath).read_bytes()
        payload = json.loads(raw)
        records[name] = {
            "path": relpath,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "schema_version": payload.get("schema_version"),
            "generated_at_utc": payload.get("generated_at_utc"),
            "mode": payload.get("mode"),
        }
    screen = json.loads((root / FILES["screen"]).read_text())
    guard = json.loads((root / FILES["guard"]).read_text())
    health = json.loads((root / FILES["delivery"]).read_text())
    findings = []
    screen_at = timestamp(screen.get("generated_at_utc"))
    source_at = timestamp(screen.get("source_generated_at_utc"))
    guard_at = timestamp(guard.get("generated_at_utc"))
    delivery_at = timestamp(health.get("generated_at_utc"))
    for name, dt in [("screen", screen_at), ("source", source_at), ("guard", guard_at), ("delivery", delivery_at)]:
        if dt is None:
            findings.append("INVALID_TIMESTAMP:" + name)
    if screen_at and source_at and source_at > screen_at:
        findings.append("SOURCE_NEWER_THAN_REPORT")
    if screen_at and guard_at and abs((guard_at-screen_at).total_seconds()) > 300:
        findings.append("GUARD_REPORT_TIME_MISMATCH_GT_5M")
    if screen_at and delivery_at and abs((delivery_at-screen_at).total_seconds()) > 300:
        findings.append("DELIVERY_REPORT_TIME_MISMATCH_GT_5M")
    evaluations = screen.get("evaluations")
    coins = guard.get("coins")
    if not isinstance(evaluations, list) or not isinstance(coins, dict):
        findings.append("MISSING_EVALUATIONS_OR_GUARD")
    else:
        names = [e.get("coin") for e in evaluations if isinstance(e, dict)]
        if len(names) != len(evaluations) or any(not isinstance(name, str) or not name for name in names):
            findings.append("INVALID_SCREEN_ASSET_ENTRY")
        if len(names) != len(set(names)):
            findings.append("DUPLICATE_SCREEN_ASSET")
        if set(names) != set(coins):
            findings.append("COIN_COVERAGE_MISMATCH")
        for entry in evaluations:
            if not isinstance(entry, dict):
                continue
            coin = entry.get("coin")
            gate = coins.get(coin, {})
            if gate.get("score") != entry.get("score") or gate.get("original_tier") != entry.get("tier"):
                findings.append("SCORE_GUARD_MISMATCH:" + str(coin))
    return {
        "manifest_schema": 1,
        "purpose": "research_report_provenance_not_trade_authorization",
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "files": records,
        "screen_source_generated_at_utc": screen.get("source_generated_at_utc"),
        "asset_count": len(evaluations) if isinstance(evaluations, list) else None,
        "warning": "Frozen report files are not live prices. CI success does not imply fresh market data or profitable signals.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="dashboard/engine-manifest.json")
    args = parser.parse_args()
    result = build_manifest()
    target = ROOT / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "findings": result["findings"], "output": str(target)}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
