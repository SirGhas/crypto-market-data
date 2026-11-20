# Stable market engine — v5.5.0 (frozen baseline)

**Status:** protected-by-process baseline, not independently validated profitable trading software.

**Pinned source commit:** `4177179207c48f3c6f13443ce723ba6e77711391` (original `main` on 2026-11-19).

**Production policy:** This branch is the frozen *official research baseline*. Never commit experiments, data refreshes, or test prototypes here. Work in `lab/market-engine-next`. Promote a candidate only after tests pass, output diffs and risk vetoes are reviewed, and an explicit release decision is recorded. Never merge the open recovery PR into `main` just to run tests.

**Current approved functionality:** v5.3 weighted 4h/1h/15m multi-asset screener; v5.4.8 unified risk/publication veto; v5.5.0 delivery-health reporting. No orders, no live trading authorization, no proven out-of-sample profitability.

**Caution:** Reports under `data/` are frozen historical snapshots, not live quotes. The snapshot may be stale. The stable branch was pinned before later RECOVERY tests; the tests were performed in the isolated recovery/lab branch and are not a claim of live strategy validation.

**Operator UI:** `dashboard/index.html` displays the pinned baseline reports. To run an updated engine, use an existing approved GitHub Actions workflow on `main` via Actions; those new results do NOT silently overwrite this pinned release. A later promotion must explicitly select a tested candidate and snapshot.
