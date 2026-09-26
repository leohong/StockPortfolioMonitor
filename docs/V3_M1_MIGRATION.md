# V3 M1 Migration — Versioning and Schema Foundation

## Scope

M1 adds version identity and separate V3 snapshot storage. It does not calculate Market Regime, V3 evidence, V3 Market State, significance, or scenarios, and it does not alter the UI.

## Forward migration

Opening the database through `src.database.db.connect` initializes the existing V2 schema and then runs ordered migrations from `src.database.migrations`.

Migration 7 creates only:

- `analysis_versions`, keyed by `analysis_version + ruleset_version`;
- `snapshot_v3_daily`, keyed by `ticker + market_date + analysis_version + ruleset_version`.

The migration is transactional and idempotent. A failed migration rolls back its schema changes and does not add its `schema_version` row.

V3 writers must register an immutable version record before persisting a snapshot. A version records the analysis version, ruleset version, schema version, creation time, Git commit, and deterministic configuration SHA256.

同一 ticker、market date、analysis version 與 ruleset version 的 V3 快照也是不可變的。完全相同的重送可安全略過；內容不同的覆寫會被拒絕，新的計算規則必須使用新的 ruleset version。

Existing rows in `analysis_snapshots` remain implicit V2 artifacts. `src.snapshots.v2_adapter` labels them in memory and does not update the database.

## Compatibility

- No existing V2 table, column, primary key, or row is modified.
- V2 services continue to read `analysis_snapshots`, `evidence_daily`, `market_stage_daily`, and `change_events`.
- The same ticker and market date may exist in both `analysis_snapshots` and `snapshot_v3_daily`.
- M1's V3 snapshot payload is a versioned storage envelope. Later phases may add normalized V3 tables without changing V2 history.

## Practical rollback

Before any V3 rows exist, stop the application and execute these statements in a transaction:

```sql
DROP TABLE snapshot_v3_daily;
DROP TABLE analysis_versions;
DELETE FROM schema_version WHERE version = 7;
```

Once V3 records exist, export or preserve both new tables before rollback. Never drop or rewrite the V2 tables. Application rollback can also leave the additive tables in place because V2 readers do not query them.

## Verification

The M1 tests cover migration initialization and idempotency, transactional rollback, deterministic config hashing, immutable registry identity, required registration, and same-date V2/V3 coexistence.

Acceptance results on 2026-09-26:

- focused M1 suite: `6 passed`;
- full regression suite: `71 passed`;
- production schema versions: 1 through 7;
- production V2 snapshot count before/after migration: 304 / 304;
- production V2 snapshot SHA256 before/after: `a03be2288dac60544b2aab4575a04b078ecdcd38e3e54d0f10b4b27cdad67389` / identical;
- V2 Portfolio Radar, Stock Detail, and existing export control smoke check: passed.

M2 benchmark and regime work has not started.
