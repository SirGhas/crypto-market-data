# LAB dashboard — operating instructions

## What exists
- `dashboard/index.html`: Persian RTL, read-only web dashboard; GitHub raw JSON for frozen stable vs moving main; GitHub Actions public run history; all displayed times converted to Asia/Tehran.
- `.github/workflows/lab-acceptance.yml`: integrated unit tests and downloadable dashboard preview.
- `.github/workflows/lab-dashboard-pages.yml`: opt-in GitHub Pages deployment, gated by tests.

## Important limitations
- The dashboard does NOT start a GitHub workflow directly. Its button opens GitHub Actions for authenticated manual execution.
- GitHub Pages must be enabled in repository Settings → Pages → Build and deployment → Source: GitHub Actions. If the repository is private or the account does not permit Pages, deployment will not work until permissions/settings permit it.
- A workflow newly added only on a feature branch may not appear in the manual Actions workflow list until it exists on the default branch. DO NOT merge experimental engine code to main to expose it. Instead first promote a reviewed *UI-only deployment workflow* to the default branch; keep the engine and tests isolated in lab.
- The stable baseline is pinned at original commit 4177179207c48f3c6f13443ce723ba6e77711391; UI/documentation additions do not imply strategy revalidation.
- GitHub public API requests can be rate limited and do not expose private repository data to anonymous browsers.
- A successful GitHub Actions job does NOT prove signals are current, profitable or trade-authorized.
- Historical stable reports do not auto-update; selecting main displays moving research snapshots, not a stable release.
- No credentials or GitHub tokens should be pasted into the dashboard.

## Safe promotion policy
1. Run the combined suite in `lab/market-engine-next`.
2. Review actual output parity, risk veto behavior, data provenance, fees/slippage, and the user-facing UI.
3. Approve a specific immutable candidate SHA; only then promote relevant files to a new stable release branch.
4. Never silently merge PR #5 or PR #4 into main.
