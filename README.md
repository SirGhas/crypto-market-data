# Crypto Market Data
Hourly OHLCV snapshots for 10 watchlist coins from Kraken public REST API, in 5m, 15m, 1h and 4h intervals. No API key. Data: `data/market.json` after first successful run.

**Important:** Kraken USD markets are not Binance USDT markets. Not all symbols may be supported. Individual errors are reported in JSON. Forming candles are excluded. No BTC.D or USDT.D, and no X/BTC data in this initial version. Github schedules can be delayed. Always inspect timestamps and errors before interpreting results; this is not an automated buy-signal service.

Go to Actions > Update crypto data > Run workflow for a manual test.
