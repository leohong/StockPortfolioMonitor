import duckdb
import pytest

from src.database.db import connect
from src.database.migrations import apply_migrations


def test_migration_7_initializes_once_and_preserves_v2_schema(tmp_path):
    path = tmp_path / "migration.duckdb"
    with connect(path) as db:
        db.execute("INSERT INTO analysis_snapshots(ticker,market_date,close,market_stage,structure_state,bullish_evidence_count,bearish_evidence_count,warning_count,data_quality_status,created_at) VALUES ('3702','2026-09-24',117.5,'TRANSITION','DOWNTREND_STRUCTURE',1,1,1,'PASS',current_timestamp)")
        before = db.execute("SELECT * FROM analysis_snapshots").fetchall()
        assert db.execute("SELECT version FROM schema_version ORDER BY version").fetchall() == [(1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,), (10,), (11,), (12,)]
    with connect(path) as db:
        assert apply_migrations(db) == []
        assert db.execute("SELECT * FROM analysis_snapshots").fetchall() == before
        assert {row[0] for row in db.execute("SHOW TABLES").fetchall()} >= {"analysis_versions", "snapshot_v3_daily", "benchmark_daily", "regime_daily", "trend_quality_daily", "momentum_state_daily", "relative_strength_daily", "participation_daily", "capital_flow_daily", "positioning_daily", "volatility_daily", "anchored_vwap_daily", "location_zones", "location_state_daily", "evidence_v3_daily", "market_state_v3_daily"}


def test_failed_migration_rolls_back_schema_and_version():
    db = duckdb.connect(":memory:")
    db.execute("CREATE TABLE schema_version(version INTEGER PRIMARY KEY)")
    db.executemany("INSERT INTO schema_version VALUES (?)", [(number,) for number in range(1, 9)])
    with pytest.raises(duckdb.Error):
        apply_migrations(db, {9: "CREATE TABLE should_rollback(id INTEGER); SELECT * FROM missing_table;"})
    assert db.execute("SELECT count(*) FROM schema_version WHERE version=9").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='should_rollback'").fetchone()[0] == 0
