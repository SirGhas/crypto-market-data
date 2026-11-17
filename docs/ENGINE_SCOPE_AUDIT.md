# Full-engine scope audit — 2026-11-17

## Purpose
The October 2026 SMA walk-forward is **only a baseline diagnostic**, not the user's market-analysis engine and not a valid end-to-end strategy comparison. Never label its return, win rate, or signal count as full-engine performance.

## Confirmed from code
- `causal_sma_backtest.py`: 5/20 daily SMA cross, single asset, one daily timeframe, hypothetical close entry.
- `walkforward_audit.py`: replays that baseline for October; not multi-strategy.
- `paired_historical_benchmark.py`: four factor keys (trend, momentum, volume, macro), **equal** weights, and no factors supplied by the live audit; hence multifactor status NOT_EVALUABLE.
- `paper_signal_gate.py`: 15m candle freshness and safety gating, not a weighted timeframe decision.
- `full_engine_acceptance.py`: checks 13 named component evidence contracts, but these are not themselves implemented strategies.
- `docs/index.html`: run status and placeholders, not the real engine's signals.

## Critical missing contracts — block full-engine claims
1. **Strategy registry:** enumerate all intended strategies and their exact signals, inputs, conflict-resolution and parameters; obtain authoritative earlier specification before assigning weights.
2. **Timeframe weights:** restore documented 15m/1h/4h/1d/etc weights and alignment/contradiction policy; current daily-only SMA cannot substitute for them.
3. **Data provenance:** as-of timestamps, independent timeframe OHLCV, asset coverage, macro and news point-in-time availability, missing-data handling.
4. **Signal aggregation:** normalized directional scores, reliability, consensus and vetoes; no default equal weights silently substituted.
5. **Risk:** position sizing, volatility, drawdown, exposure, spread/slippage and portfolio constraints.
6. **Evaluation:** same signal engine at each historical decision time; no future leakage; next executable candle entry, round-trip fees, slippage, and multiple market regimes.
7. **Operational:** evidence-backed alerts and a real user-facing dashboard; separate unit-test green from full-engine acceptance.

## Required evaluation matrix
Each test report must identify: experiment ID, git SHA, dataset and cutoff, strategy IDs and versions, timeframe IDs and weights, source and data coverage, feature timestamps, signal contributions, vetoes, risk decision, outcome assumptions, acceptance failures, and whether this is BASELINE_ONLY or FULL_ENGINE.

## Decision
Do not optimize or present the SMA baseline as a replacement for the multi-strategy engine. First recover the original strategy/timeframe specification; then implement the registry and a strict missing-component gate, and only then run full-engine historical comparisons. Unknown weights must remain UNKNOWN, not guessed.
