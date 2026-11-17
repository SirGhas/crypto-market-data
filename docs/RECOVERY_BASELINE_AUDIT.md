# Recovery decision — 2026-11-17

## Selected baseline
**main / v5.5.0 screening and guard pipeline**, branched as `recovery/v5-5-core-audit`. This is the closest **implemented architecture** to the multi-asset, weighted, multi-timeframe, capital-preservation-oriented engine. **Not approved for live trading, reliable profitability, or investment decisions.**

## Evidence in main
- `dual_screen_v53.py`: 10 assets, 4h/1h/15m closed candles, weighted score 30 static levels +25 volume +15 4h trend +15 risk/reward +5 relative BTC +5 lower timeframes +5 BTC/dominance =100. Outputs tiers, source/score components, and blocks stale data.
- `signal_engine.py`: distinct 5m/15m/1h/4h input frames; 4h BTC and relative-strength vetoes, 1h breakout, 15m confirmation, volume >=1.3, invalid/wide-stop rejection. Watch only, not orders.
- `unified_guard_v548.py`: source, continuity, age, price parity and liquidity publication vetoes, with special BTC cross safeguards.
- `delivery_health_v550.py`: stale/unverified feed audit and durable undelivered-event queue; no fake delivery claims.
- `data/dual_screen_v53.json`, `data/unified_guard_v548.json`, `data/delivery_health_v550.json`: operational snapshots of above.
- `engine/alpha_walkforward_v171.py`, `engine/alpha_score_audit_v180.py`, `engine/alpha_offline_replay_v207.py`: useful historical evidence/provenance tooling, explicitly research only and **not** validated live multi-strategy execution.

## Divergence found
`research/alpha-v2-0-9-slvon-recovery` added an **independent** `causal_sma_backtest.py` and `btc_oct17_historical_audit.py`. Its October 31-day performance is a single daily 5/20 SMA crossover, **not** the v5.3 weighted screener or the multi-timeframe signal engine. The standalone 13-component acceptance rubric cannot establish functional parity with v5.5.0.

## Known gaps, not to be disguised
1. v5.5.0 is **screening/research-only**, not a statistically validated profitable trading system; no order authorization.
2. The 100-point weights are heuristic scores, **not** empirically calibrated strategy allocations or probabilities.
3. BTC.D/USDT.D are snapshots, not verified multi-timeframe dominance candles; code explicitly caps corresponding score.
4. R:R from levels excludes trading costs/slippage; static levels are heuristic, not institutional order-book levels.
5. Several BTC cross feeds are UNVERIFIED; latest health report shows 64 PASS and 20 UNVERIFIED.
6. Notification outbox has pending events but no configured delivery transport.
7. No demonstrated independent full-engine walk-forward, out-of-sample evaluation, drawdown controls, or market-regime calibration.
8. Iran equities, tokenized metals, macro/geopolitics, and portfolio-wide capital allocation must be assessed as distinct modules, not inferred from crypto v5.5.

## Recovery constraints
- Preserve `main` and previous research branches unchanged.
- Use this branch for read-only auditing, tests and **parity** verification before any model modifications.
- Every test must run the **existing v5.5 core**, not a substituted SMA strategy.
- Do not silently adjust the seven score weights.
- Reject stale, missing, future-dated, unverified or conflicting evidence; NO_SIGNAL / WATCH_ONLY is legitimate.
- Explicitly separate software correctness, data integrity, signal predictive validity, and capital-risk safety.
- No live trading, automatic orders, or misleading claim of financial reliability until independently validated.

## First acceptance milestones
A. Reproduce the same v5.3 per-asset score components and v5.4.8 vetoes from a frozen market snapshot.
B. Test 4h/1h/15m perturbations separately and assert intended contribution and blocking behavior.
C. Verify price parity, liquidity, source freshness, missing BTC cross, dominance uncertainty.
D. Compare baseline vs strategy stack on causal historical data with fees/slippage and untouched holdout periods.
E. Expand to portfolio-wide risk and additional markets **after** above passes.
