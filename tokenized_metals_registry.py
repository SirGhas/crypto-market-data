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
    "XLVON": MetalAsset(
        ticker="XLVON", metal="silver", market_pair=None, venue=None,
        identity_verified=False, data_enabled=False, analysis_enabled=False,
        status="pending_exact_token_identity_and_spot_pair_confirmation",
    ),
}

def research_watchlist():
    return tuple(METALS)

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
