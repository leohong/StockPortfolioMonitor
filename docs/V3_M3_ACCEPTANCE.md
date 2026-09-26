# V3 M3 Acceptance — Trend Quality, Momentum and Relative Strength

## Implemented scope

- Added additive migration 9 with versioned `trend_quality_daily`, `momentum_state_daily`, and `relative_strength_daily` tables.
- Added configurable trend thresholds in `config/settings.yaml`.
- Added Trend Quality features: MA5/20/60/120, MA20/60/120 five-session slopes, price distance from MA20/60, MA20/60 separation, and 20-session persistence.
- Preserved the existing Wilder RSI14 definition and added RSI five-session change, 30/50/70/80 crossing metadata, ROC20, and confirmed RSI divergence.
- Added exact-date TAIEX relative strength for 20/60/120 sessions plus raw and indexed relative-strength lines.
- Added explicit sector benchmark missing state. No sector RS value is generated without a reliable historical sector benchmark.
- Added unadjusted-price basis and rolling corporate-action warning metadata to relative strength.

M3 does not replace V2 Market Stage and does not implement the V3 Evidence Vector or V3 Market State.

## Deterministic states

Trend states are derived from the configured moving-average relationships, slopes, distances, and persistence. Momentum states use only RSI14, its recent change, ROC20, and confirmed divergence observations. Relative-strength states use stock return minus aligned TAIEX return and the direction of the RS line.

No total stock score, probability, target price, or LLM-derived state is produced.

## Point-in-time controls

- All features sort observations chronologically and use backward rolling windows.
- TAIEX data joins stock data on the exact market date with no forward fill.
- A missing benchmark date produces `INSUFFICIENT_DATA` and `benchmark_date_alignment`.
- RSI divergence only becomes visible on or after the second pivot's `confirmation_date`.
- Tests append future data and verify that earlier relative-strength output is unchanged.
- Every stored row includes analysis version, ruleset version, calculation time, and source dates.
- Rows are immutable within a ticker/date/version/ruleset identity.

## Corporate-action handling

M3 continues to use the V2 official raw, unadjusted price series. It does not silently change indicator definitions or back-adjust prices. Relative-strength rows state `price_basis = UNADJUSTED`; if an official `X` adjustment marker occurred within the 120-session window, `corporate_action_warning = true`.

This makes the limitation auditable. It does not claim that relative strength is corporate-action neutral.

## Production verification

Ruleset: `m3-trend-momentum-rs-v1`  
Code commit: `1aa559c`  
Ticker/date: `3702 / 2026-09-24`

```text
Trend Quality: TREND_EMERGING
Momentum: ACCELERATING
Relative Strength: IMPROVING
RS market 20D:  +11.3059716086%
RS market 60D:   +4.6794502121%
RS market 120D: -13.9166869804%
Sector RS 20D: missing (sector_benchmark)
Price basis: UNADJUSTED
Corporate-action warning: true
```

An independent DuckDB query using aligned closes and `lag(..., 20/60/120)` reproduced the stored RS values within floating-point precision.

Each M3 table contains 304 rows from 2025-07-01 through 2026-09-24. Existing V2 `analysis_snapshots` still contains 304 rows.

## Tests

- M3 focused suite: `9 passed`.
- Initial full regression suite: `84 passed`.
- Final full regression suite after production verification: `84 passed in 7.67s`.
- Tests cover MA120 warmup, trend states, preserved RSI values, ROC20, divergence confirmation timing, manually calculated 20/60/120-day RS, missing benchmark alignment, missing sector benchmark, corporate-action warning, future-data isolation, migration idempotency, and rollback.

## Rollback

M3 application rollback can leave the additive tables in place because V2 and M2 readers do not query them. Before data exists, migration 9 can be reversed by dropping only:

```sql
DROP TABLE relative_strength_daily;
DROP TABLE momentum_state_daily;
DROP TABLE trend_quality_daily;
DELETE FROM schema_version WHERE version = 9;
```

Once M3 records exist, preserve/export the three tables before removing them. Never change or delete V2 tables as part of an M3 rollback.

M4 has not started.
