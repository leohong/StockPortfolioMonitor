# V3 M2 Acceptance — Benchmark and Market/Sector Regime

## Implemented scope

- Added schema migration 8 with additive `benchmark_daily`, `sector_classification`, `sector_benchmark_daily`, `market_breadth_daily`, and versioned `regime_daily` tables.
- Added official TWSE TAIEX monthly OHLC plus market volume/turnover retrieval with SHA256 cache metadata.
- Added official TWSE listed-company classification snapshots with honest `available_date` and `effective_from` dates.
- Added a deterministic point-in-time Market Regime engine using benchmark MA20/60, five-session slopes, RSI14, and ATR14%.
- Added structured supporting evidence, contradicting evidence, missing inputs, source dates, and evidence-completeness classes.
- Added explicit insufficient Sector Regime output when the historical classification or sector benchmark is unavailable.
- Added a small Stock Detail Regime strip. Existing V2 Market Stage remains visible and unchanged.

No V3 trend, momentum, relative-strength, evidence-vector, Market State, significance, or scenario feature was implemented.

## Official production data

Sources:

- TAIEX OHLC: `https://www.twse.com.tw/indicesReport/MI_5MINS_HIST`
- TAIEX market totals: `https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK`
- Listed-company classification: `https://openapi.twse.com.tw/v1/opendata/t187ap03_L`

Persisted TAIEX data contains 304 official daily rows from 2025-07-01 through 2026-09-24. Every row retains its source URLs, retrieval timestamp, official flag, index-point price unit, share volume unit, and cached raw-response SHA256 metadata.

For 2026-09-24 the persisted result is:

```text
Market Regime: RISK_ON_TREND
Confidence class: CONFIRMED
Ruleset: m2-regime-v2
Code commit: 87857e7
Missing optional input: market_breadth
```

The supporting observations are close above MA20, MA20 above MA60, positive MA20 and MA60 five-session slopes, and RSI14 above 50. Confidence is evidence completeness, not a probability.

Ticker 3702 has official classification `TWSE-29`, but that snapshot became available on 2026-09-25. It is not applied to the 2026-09-24 historical state. Sector Regime therefore remains `INSUFFICIENT_DATA` with `sector_classification_as_of` explicitly missing. No historical classification or sector index was fabricated.

Reliable breadth history was not integrated in M2. `market_breadth` remains explicitly missing and the empty breadth table does not imply zero values.

## Point-in-time and compatibility verification

- Calculations sort by market date and use backward rolling windows only.
- `regime_as_of` filters all benchmark rows to the requested date before calculation.
- Tests verify that adding future bars cannot change the earlier regime.
- Classification queries require both `effective_from <= as_of` and `available_date <= as_of`.
- Missing benchmark history produces `INSUFFICIENT_DATA` rather than fabricated evidence.
- Regime rows are immutable within one analysis/ruleset identity.
- Existing 304 V2 `analysis_snapshots` rows remain present and unchanged.
- The Stock Detail smoke check showed the V3 Regime strip, current market regime, explicit sector limitation, existing V2 Market Stage, and existing export controls together.

## Test results

- M2 focused suite: `12 passed` before the production-data check.
- Date-normalization/point-in-time focused suite after correcting the official ROC report date: `6 passed`.
- Full suite before the production-data check: `77 passed`.
- Final full regression suite after the ROC-date correction: `77 passed in 12.99s`.

M3 has not started.
