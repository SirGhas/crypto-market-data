"""Fail-closed registry for proposed tokenized precious-metals research assets.

A requested ticker is not proof of exchange instrument availability or identity.
This registry does not enable signal generation or trading.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class MetalAsset:
    ticker: str
    metal: str
    market_pair: str | None
    venue: str | None
    identity_verified: bool
    data_enabled: bool
    analysis_enabled: bool
    status: str

METALS = {
    "XAUT": MetalAsset(
        ticker="XAUT", metal="gold", market_pair="XAUT-USDT", venue="OKX Spot",
        identity_verified=True, data_enabled=False, analysis_enabled=False,
        status="pending_closed_candle_quality_and_reference_price_validation",
    ),
    "SLVON": MetalAsset(
        ticker="SLVON", metal="silver", market_pair="SLVON/USDT", venue="Phemex Spot",
        identity_verified=True, data_enabled=False, analysis_enabled=False,
        status="price_only_research_candidate_volume_and_reference_unverified",
    ),
}

def research_watchlist():
    return tuple(METALS)

def silver_price_snapshot(evidence: dict) -> dict:
    """Restricted engine-facing research adapter; never authorize full analysis."""
    from decimal import Decimal
    from datetime import datetime
    if evidence.get("asset") != "SLVON" or evidence.get("venue") != "Phemex Spot":
        raise ValueError("SLVON_IDENTITY_MISMATCH")
    if evidence.get("status") != "PRICE_SCALE_VERIFIED_VOLUME_SCALE_AND_REFERENCE_PARITY_PENDING":
        raise ValueError("SLVON_PRICE_NOT_VALIDATED")
    frame = evidence["frames"]["15m"]
    price = Decimal(frame["latest_normalized_close_usdt"])
    timestamp = datetime.fromisoformat(frame["last_closed_at_tehran"])
    if not price.is_finite() or price <= 0 or timestamp.utcoffset() is None:
        raise ValueError("SLVON_INVALID_SNAPSHOT")
    return {"ticker": "SLVON", "close_usdt": str(price),
            "closed_at": timestamp.isoformat(), "research_only": True,
            "volume_enabled": False, "reference_parity_enabled": False,
            "analysis_enabled": False, "signals_enabled": False, "trading_enabled": False}


def eligible_for_analysis(ticker: str) -> bool:
    asset = METALS[ticker]
    return bool(asset.identity_verified and asset.market_pair and
                asset.venue and asset.data_enabled and asset.analysis_enabled)

def approved_market_pair(ticker: str) -> str:
    if not eligible_for_analysis(ticker):
        raise ValueError(f"METAL_RESEARCH_FEED_NOT_APPROVED:{ticker}")
    return METALS[ticker].market_pair

RESEARCH_ONLY = True
SIGNALS_ENABLED = False
TRADING_ENABLED = False
TRADE_AUTHORIZED = False
