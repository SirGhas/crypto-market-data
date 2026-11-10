"""Read-only Phemex SLVON spot market probe; fail closed on uncertain metadata."""
import argparse
import datetime as dt
import json
import math
from decimal import Decimal, InvalidOperation
import urllib.parse
import urllib.request

BASE = "https://api.phemex.com"
RESOLUTIONS = {"15m": 900, "1h": 3600, "4h": 14400}
CANDIDATES = ("sSLVONUSDT", "SLVONUSDT")


def get_json(path, params=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "crypto-market-research-read-only/1"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def find_spot_product(payload):
    data = payload.get("data", payload)
    products = data.get("products", []) if isinstance(data, dict) else []
    matches = [p for p in products if isinstance(p, dict)
               and p.get("symbol") in CANDIDATES
               and str(p.get("type", "")).lower() == "spot"]
    if len(matches) != 1:
        raise ValueError("SLVON_SPOT_PRODUCT_NOT_UNAMBIGUOUS")
    product = matches[0]
    if str(product.get("status", "Listed")).lower() in ("delisted", "disabled", "suspended"):
        raise ValueError("SLVON_SPOT_PRODUCT_NOT_ACTIVE")
    return product


def validate_rows(rows, resolution, now):
    if not isinstance(rows, list):
        raise ValueError("INVALID_KLINE_ROWS")
    clean = {}
    for row in rows:
        if not isinstance(row, list) or len(row) < 9:
            raise ValueError("MALFORMED_KLINE_ROW")
        timestamp, interval = int(row[0]), int(row[1])
        if interval != resolution or timestamp % resolution:
            raise ValueError("KLINE_ALIGNMENT_MISMATCH")
        # Phemex values are exchange-scaled; no unverified price/volume scaling.
        o, h, l, c, v = (float(row[i]) for i in (3, 4, 5, 6, 7))
        if not all(map(math.isfinite, (o, h, l, c, v))):
            raise ValueError("NONFINITE_KLINE")
        if not (0 < l <= min(o, c) <= max(o, c) <= h and v >= 0):
            raise ValueError("INVALID_KLINE_OHLCV")
        if timestamp + resolution <= now - 2:
            if timestamp in clean and clean[timestamp] != row:
                raise ValueError("CONFLICTING_DUPLICATE_KLINE")
            clean[timestamp] = row
    times = sorted(clean)
    if len(times) < 233:
        raise ValueError("INSUFFICIENT_CLOSED_KLINES")
    recent = times[-233:]
    if any(b - a != resolution for a, b in zip(recent, recent[1:])):
        raise ValueError("KLINE_HISTORY_GAP")
    if now - (recent[-1] + resolution) > resolution + 180:
        raise ValueError("STALE_CLOSED_KLINE")
    if recent[-1] + resolution > now:
        raise ValueError("FUTURE_CLOSED_KLINE")
    return {"closed_candles": len(times),
            "last_closed_at_utc": dt.datetime.fromtimestamp(recent[-1] + resolution, dt.timezone.utc).isoformat(),
            "nonzero_volume_last_233": sum(float(clean[t][7]) > 0 for t in recent),
            "scaled_prices_not_yet_normalized": True}


def normalize_price(raw, product):
    scale = product.get("priceScale")
    if type(scale) is not int or not 0 <= scale <= 18:
        raise ValueError("INVALID_PHEMEX_PRICE_SCALE")
    try:
        value = Decimal(str(raw)) / (Decimal(10) ** scale)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("INVALID_SCALED_PRICE") from exc
    if not value.is_finite() or value <= 0:
        raise ValueError("INVALID_SCALED_PRICE")
    return str(value)


def probe(now=None):
    if now is None:
        now = int(dt.datetime.now(dt.timezone.utc).timestamp())
    result = {"asset": "SLVON", "venue": "Phemex Spot",
              "research_only": True, "data_enabled": False,
              "analysis_enabled": False, "signals_enabled": False,
              "trading_enabled": False, "trade_authorized": False,
              "status": "BLOCKED", "frames": {}}
    try:
        product = find_spot_product(get_json("/public/products"))
        result["exchange_symbol"] = product["symbol"]
        result["product_scale_metadata"] = {
            key: product[key] for key in (
                "priceScale", "valueScale", "qtyScale", "pricePrecision",
                "baseCurrency", "quoteCurrency", "type", "status"
            ) if key in product
        }
        for frame, resolution in RESOLUTIONS.items():
            payload = get_json("/exchange/public/md/v2/kline",
                               {"symbol": product["symbol"], "resolution": resolution, "limit": 500})
            if payload.get("code") != 0:
                raise ValueError("PHEMEX_KLINE_API_ERROR")
            rows = payload.get("data", {}).get("rows")
            result["frames"][frame] = validate_rows(rows, resolution, now)
            latest = max((r for r in rows if int(r[0]) + resolution <= now - 2), key=lambda r: int(r[0]))
            result["frames"][frame]["latest_normalized_close_usdt"] = normalize_price(latest[6], product)
            result["frames"][frame]["latest_raw_scaled_ohlcv"] = {
                "timestamp": latest[0], "open": latest[3], "high": latest[4],
                "low": latest[5], "close": latest[6], "volume": latest[7]
            }
        result["status"] = "PRICE_SCALE_VERIFIED_VOLUME_SCALE_AND_REFERENCE_PARITY_PENDING"
    except Exception as exc:
        result["reason"] = str(exc)[:180]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/slvon_phemex_probe.json")
    args = parser.parse_args()
    result = probe()
    from pathlib import Path
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    if result["status"] == "BLOCKED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
