# V3 Migration Audit — M0 Repository Audit and Baseline Freeze

Audit date: 2026-09-26 (Asia/Taipei)  
Baseline commit: `d14a50553ecd3c9cb335882940b085350a3f1b9e`  
Scope: M0 only. No analytical rules, schemas, tables, or historical records were changed.

## Baseline status

The reproducible baseline command is:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result: **65 passed in 19.93s**. No test failures were observed. The suite is offline and uses fixtures or temporary databases. The working tree already contained two untracked user artifacts before M0: `V3_MIGRATION_PLAN.md` and `3702_2026-09-24_120D.png`; M0 did not modify the PNG.

The Streamlit application was running at `http://127.0.0.1:8501/`. A UI smoke check confirmed these existing pages and major controls:

| Page | Verified behavior |
|---|---|
| Portfolio Radar | Latest 3702 snapshot, attention counts, search, stage/alert filters, changed-only control, sortable table |
| Stock Detail | Yesterday vs Today, latest changes, Market Stage, structure, seven evidence cards, synchronized five-layer chart, CSV and 3200×2200 PNG export controls |
| Market Stage Timeline | Timeline, historical date selection, saved snapshot/evidence review |
| Holdings Compare | Existing comparison page loads; configured portfolio currently contains one holding, so a 2–5 stock comparison cannot be exercised with production holdings |
| Data Quality | Dataset provenance and quality audit page loads |

## Current repository architecture

The application is a compact Streamlit/DuckDB system rather than the larger target package layout shown in the V3 plan. V3 should extend these actual paths in place.

```text
app.py
  -> src/ui.py
       -> portfolio_service.py / review_service.py / stock_service.py
       -> stock_chart.py / export_service.py

stock_service.py
  -> TWSE providers -> normalizers -> validators -> DuckDB raw tables
  -> indicators/core.py + analysis/phase2_metrics.py
  -> analysis/price_structure.py
  -> analysis/evidence.py
  -> analysis/market_stage.py
  -> analysis/snapshot.py
  -> DuckDB analysis tables

Portfolio/Timeline/Compare/Data Quality
  -> direct read queries over V2 snapshots, events, evidence and source tables
```

### Data acquisition and provenance

- `src/data/providers/twse.py` retrieves official monthly TWSE `STOCK_DAY` OHLCV.
- `src/data/providers/twse_phase2.py` retrieves official daily `T86` institutional and `MI_MARGN` margin/short data.
- Responses are archived under `data/cache` with SHA256 metadata. Phase 2 reuses cached official payloads.
- Normalized rows preserve source URL, source type, official flag, retrieval time, and units.
- OHLCV volume and institutional flow use shares. Margin/short data use TWSE trading units.
- No benchmark, sector classification, sector benchmark, or breadth provider exists yet.

### Deterministic analysis flow

1. `src/indicators/core.py`: MA5/20/60, Wilder RSI14, volume MA20 and ratio.
2. `src/analysis/phase2_metrics.py`: institutional 3/5/10/20-day sums and margin 1/5/10/20-day changes.
3. `src/analysis/price_structure.py`: confirmed pivots, HH/HL/LH/LL, structure snapshots, two support/resistance levels.
4. `src/analysis/evidence.py`: exactly seven V2 evidence factors.
5. `src/analysis/market_stage.py`: A–G/transition stage rules.
6. `src/analysis/snapshot.py`: denormalized V2 snapshots and raw change events.
7. `src/services/stock_service.py`: phase orchestration and destructive per-ticker recomputation of derived V2 tables.

### Current pages and services

- `src/ui.py` contains all five Streamlit pages and V2 display assumptions.
- `src/services/portfolio_service.py` queries the latest V2 snapshot and event severity.
- `src/services/review_service.py` supplies Timeline, historical review, Compare, and Data Quality.
- `src/charts/stock_chart.py` renders price, volume, institutional, margin, and RSI panels.
- `src/services/export_service.py` exports the same current V2 snapshot/evidence/events to CSV and PNG.

## Actual DuckDB inventory

Database: `data/stocks.duckdb`. Schema registry rows are `(1)` through `(6)`. Schema creation is currently a single idempotent SQL string in `src/database/db.py`; there is no ordered migration runner or rollback mechanism.

| Table | Primary identity | Rows | Purpose |
|---|---|---:|---|
| `ohlcv_daily` | ticker, market_date | 304 | Official OHLCV and provenance |
| `institutional_daily` | ticker, market_date | 250 | Foreign/trust/dealer daily flow |
| `margin_daily` | ticker, market_date | 250 | Margin and short activity |
| `data_quality_events` | none | 4 | Validation audit JSON |
| `price_pivots` | ticker, pivot_date, pivot_kind | 56 | Confirmed pivots and comparison metadata |
| `structure_snapshots` | ticker, market_date | 304 | Daily V2 structure state |
| `price_levels` | ticker, market_date, level_type, rank | 1,023 | Daily support/resistance derivations |
| `evidence_daily` | ticker, market_date, factor | 2,128 | Seven V2 evidence records per date |
| `market_stage_daily` | ticker, market_date | 304 | V2 A–G/transition stage |
| `analysis_snapshots` | ticker, market_date | 304 | Denormalized V2 daily snapshot |
| `change_events` | ticker, market_date, change_type | 525 | V2 change events and severity |
| `schema_version` | version | 6 | Applied schema integers |

Production ranges at audit time:

- OHLCV and V2 snapshots: 2025-07-01 through 2026-09-24.
- Institutional and margin/short: 2025-09-15 through 2026-09-24.
- Production database contains ticker 3702 only.

None of the derived tables contains `analysis_version`, `ruleset_version`, `calculation_version`, `available_date`, or a configuration hash. Existing V2 records must therefore be treated as implicit `v2` artifacts rather than updated in place.

## P1–P9 mapping to V3

| Existing capability | Actual implementation | V3 disposition |
|---|---|---|
| Validated OHLCV | TWSE provider, validator, `ohlcv_daily` | Preserve |
| Institutional/margin/short | TWSE Phase 2 provider and typed tables | Preserve; reuse for flow and positioning |
| MA/RSI/volume | `indicators/core.py` | Preserve definitions; extend in later phases |
| Confirmed structure | `price_structure.py`, pivot/structure tables | Preserve no-look-ahead core; version V3 outputs separately |
| Support/resistance | `derive_levels`, `price_levels` | Preserve V2; extend to V3 confluence/location separately |
| Seven evidence factors | `evidence.py`, `evidence_daily` | Retain as V2; new V3 vector must use a new model/table |
| Market Stage | `market_stage.py`, `market_stage_daily` | Retain as V2; V3 Market State must be parallel |
| Snapshots and changes | `snapshot.py`, `analysis_snapshots`, `change_events` | Preserve; add versioned V3 snapshots/significance |
| Portfolio Radar | `portfolio_service.py`, `ui.py` | Preserve until M8 additive UI cutover |
| Timeline/Compare/Quality | `review_service.py`, `ui.py` | Preserve; make version-aware later |
| CSV/PNG export | `export_service.py` | Preserve; add V3 export input later without changing V2 history |

V3 has no implementation yet for benchmark/sector/breadth, market regime, trend quality, refined momentum, relative strength, participation state, flow persistence, positioning/crowding, volatility, AVWAP/confluence zones, multidimensional evidence, V3 Market State, significance, scenarios, or evaluation.

## Coupling inventory

### Seven-factor evidence

- `src/models.py`: `Evidence.factor` is a seven-value `Literal`.
- `src/analysis/evidence.py`: `FACTORS`, fixed creation order, fixed thresholds, and a final exact tuple assertion.
- `src/services/stock_service.py`: requires `len(evidence) == 7`, slices `evidence[-7:]`, and rebuilds all V2 evidence.
- `src/analysis/market_stage.py`: records available V2 factor names.
- `src/analysis/snapshot.py`: reduces the seven factors to bullish/bearish/warning counts.
- `src/ui.py`: fixed card labels, order, statuses, and seven-card rendering.
- `src/services/export_service.py`: fixed seven-factor labels/status colors and card layout.
- Tests: `test_phase4.py`, `test_phase5.py`, `test_phase6.py`, `test_phase8.py`, and `test_phase9.py` assert this contract.

### Old Market Stage

- `src/models.py`: fixed A–G/transition `MarketStage` literals.
- `src/analysis/market_stage.py`: all classification thresholds and prior-stage transitions.
- `src/services/stock_service.py`: phase-5 sequencing and persistence prerequisite for snapshots.
- `market_stage_daily` and `analysis_snapshots.market_stage`.
- `snapshot.py`: stage-change events.
- `portfolio_service.py`, `review_service.py`, `ui.py`, `i18n.py`, chart/timeline and filters.
- Phase 5–9 tests and exports.

### Margin interpretation

- `phase2_metrics.py`: balance deltas and a fixed 20-day percent change.
- `evidence.py`: `>=20%` becomes a V2 warning.
- `market_stage.py`: margin can help classify `E_OVERHEATED`.
- `snapshot.py`: threshold-crossing event at 20%.
- Snapshot schema, Radar, Compare, chart, i18n, exports, and Phase 2/4/5/6 tests.
- Short fields are stored and charted indirectly through quality checks, but are not used in V2 evidence/state.

### Volume interpretation

- `indicators/core.py`: MA20 and ratio.
- `evidence.py`: fixed 0.8/1.2/2.0 descriptions.
- `market_stage.py`: 1.3 contributes to overheat.
- `price_structure.py`: 1.8 selects high-volume level candidates.
- `snapshot.py`: 1.5 crossing event.
- Five-layer chart, snapshots, exports, i18n, and tests.

### Support/resistance

- `price_structure.py`: confirmed pivots, MA20/60, 10-day consolidation, and high-volume candidates; nearest two non-overlapping levels.
- `price_levels` and `PriceLevel` model.
- `evidence.py`: one neutral support/resistance card.
- `snapshot.py`: flattened S1/S2/R1/R2 and break/reclaim events.
- `review_service.py`: comparison distances.
- Stock chart annotations, UI, exports, and Phase 3/4/6/8/9 tests.

### Snapshots and change detection

- `AnalysisSnapshot`, `ChangeEvent`, `analysis_snapshots`, `change_events` have no version column.
- `stock_service.refresh_phase6` rebuilds the full series, then `persist_snapshots_and_events` deletes all records for the ticker before insertion.
- Portfolio, Timeline, Compare, Data Quality and export services query these V2 tables directly.
- Change identity is only ticker/date/type; V2 and V3 events cannot coexist in this table.

### Exports

- UI passes current Plotly figure, latest V2 snapshot, V2 evidence and V2 events directly to `export_service.py`.
- CSV schema and PNG annotations use V2 field and factor names.
- Export filenames have no analysis/ruleset version.

## Point-in-time and look-ahead audit

### Existing safeguards

- Pivot `confirmation_date` is the right-bar confirmation date.
- Structure snapshots and level derivation include only pivots confirmed on or before `as_of`.
- Indicator rolling windows and institutional/margin rolling calculations use preceding rows.
- Level derivation filters market data to `market_date <= as_of`.
- Historical review rejects V2 evidence whose `source_dates` exceed the requested market date.
- Tests cover future-confirmed pivots and a future evidence source date.

### Risks to address

1. **Derived V2 history is mutable.** Phase 3–6 persistence deletes and recomputes a ticker's full history. A later source revision, rule change, configuration change, or code change can silently rewrite old snapshots.
2. **No calculation identity.** Snapshots/evidence/stages do not record analysis version, ruleset version, config hash, or git commit, so a row cannot be reproduced unambiguously.
3. **Availability is incomplete.** Market date, retrieval time, pivot confirmation date, and evidence source dates exist in different places, but there is no common `observation_date`/`available_date` contract. Historical review checks source dates only.
4. **Historical quality leakage.** `refresh_phase6` applies the current whole-series `quality.status` to every historical snapshot rather than the quality state knowable on each date.
5. **Source revisions replace raw normalized rows.** `INSERT OR REPLACE` keeps the latest official value and warning logs, but no revision table allows exact replay of the earlier known value.
6. **Historical snapshots use current code/config.** Recalculation uses the current pivot sensitivity, level tolerance, thresholds, and implementation without storing those values per snapshot.
7. **Stage transition path is recomputed.** V2 stage uses `previous_stage`; any earlier revision can cascade through later stages.
8. **Evidence availability metadata is coarse.** Structure evidence stores pivot dates in `source_dates`, while confirmation dates live in the pivot table. Consumers that inspect evidence alone cannot prove when the pivot became knowable.
9. **No benchmark/sector effective dating exists.** M2 must never join current classifications or index constituents into historical dates without effective periods.
10. **Corporate actions remain warnings.** Unadjusted prices are explicit, but later relative-strength and return calculations could be distorted unless V3 records the chosen treatment.

## Backward-compatibility risks

1. Adding `analysis_version` directly to existing V2 primary keys could rebuild or reinterpret historical rows and break every positional `INSERT ... SELECT *`.
2. Reusing `analysis_snapshots`, `evidence_daily`, `market_stage_daily`, or `change_events` for V3 would collide on existing primary keys.
3. Renaming V2 factors, stage labels, columns, or tables would break UI mappings, exports, saved queries, P1–P9 tests, and historical rendering.
4. Replacing V2 model literals with V3 literals would make existing database rows fail Pydantic validation.
5. Adding columns to existing tables can break the repository's column-order-dependent persistence calls.
6. Portfolio/Timeline/Compare/Data Quality all query V2 tables directly and would ambiguously mix versions if versioned rows were inserted there.
7. V2 change severity (`INFO/WATCH/IMPORTANT/CRITICAL`) differs from planned V3 significance (`LOW/MEDIUM/HIGH/CRITICAL`); they require separate fields/tables.
8. Current exports assume seven evidence cards and unversioned filenames; changing defaults before M8 risks export regression.
9. Current production history has no explicit `v2` tag. A compatibility adapter or registry declaration is safer than updating all existing rows.
10. The repository has only one production holding. Multi-holding UI behavior is test-covered but production smoke validation is limited.

## Recommended M1 file changes

M1 should remain additive and must not introduce regime logic or UI redesign.

| File | Recommended change |
|---|---|
| `src/database/migrations.py` | Add an ordered, transactional migration runner with applied-version checks and documented rollback boundaries. |
| `src/database/migrations/007_v3_foundation.sql` | Add the V3 registry/foundation tables without altering V2 tables. |
| `src/analysis/versioning.py` | Define immutable analysis/ruleset/schema identifiers and deterministic config hashing. |
| `src/models_v3.py` | Add version registry and minimal V3 snapshot/evidence identity models; keep `src/models.py` V2 contracts unchanged. |
| `src/snapshots/v2_adapter.py` | Explicitly identify existing V2 snapshots as compatibility artifacts without rewriting them. |
| `src/snapshots/v3_snapshot.py` | Define the versioned V3 snapshot container only; no V3 analytical calculation yet. |
| `src/database/db.py` | Invoke the migration runner after existing V2 schema initialization; preserve all current read/write functions. |
| `tests/test_analysis_versioning.py` | Verify registry fields, deterministic config hash, and immutable identities. |
| `tests/test_migrations.py` | Verify fresh initialization, idempotency, transactional failure, and existing V2 row preservation. |
| `tests/test_v2_v3_coexistence.py` | Verify the same ticker/date can exist in V2 and V3 storage and V2 services still read the original row. |
| `docs/V3_M1_MIGRATION.md` | Record forward migration, practical rollback, and V2 preservation procedure. |

Names may be adjusted minimally to match repository conventions, but M1 should not create empty modules for later analytical phases.

## Recommended M1 database migration

Use new tables rather than changing existing V2 primary keys:

```text
analysis_versions
  analysis_version PK
  ruleset_version
  schema_version
  created_at
  git_commit
  config_hash
  deprecated

snapshot_v3_daily
  ticker
  market_date
  analysis_version
  ruleset_version
  created_at
  data_quality_status
  payload_json or only the minimal M1 identity columns
  PK (ticker, market_date, analysis_version, ruleset_version)
```

If M1 introduces empty V3 evidence/state containers for coexistence tests, place them in separate `evidence_v3_daily` and `market_state_v3_daily` tables with versioned composite keys. Do not add V3 rows to `analysis_snapshots`, `evidence_daily`, `market_stage_daily`, or `change_events`. Do not update the 304 existing V2 snapshots merely to attach a version label.

Migration 007 should be transactional and idempotent. A practical rollback is to stop V3 writers/readers and drop only the new empty V3 foundation tables; the existing V2 tables remain untouched. Once V3 data exists, rollback should preserve/export those tables rather than destroy records.

## M0 blockers and decisions required later

There is no blocker to M1.

The following are deferred to their owning phases:

- M1 must choose the durable representation for V3 snapshot payloads versus normalized columns; this must preserve versioned identity without pre-implementing later features.
- M2 must select official, historically available benchmark and sector-classification sources and define effective dating.
- Breadth availability is unknown and must remain missing until a reliable source is verified.
- Corporate-action adjustment policy must be explicit before M3 relative-strength evaluation.
- Production UI comparison is limited by the single configured holding, though automated comparison tests pass.

## M0 acceptance

- Baseline is reproducible: **yes**, commit and test command/results are recorded.
- All known failures are documented: **yes**, no automated failures; production comparison limitation and temporal/audit risks are recorded.
- Migration plan references actual code and schema: **yes**, path, table, coupling, and M1 migration inventories above reflect the repository at the baseline commit.

M0 is complete. M1 has not been implemented.
