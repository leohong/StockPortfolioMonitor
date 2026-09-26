from datetime import date, datetime, timezone

import pytest

from src.analysis.versioning import register_analysis_version, version_record
from src.database.db import connect, persist_snapshots_and_events, read_snapshots
from src.models import AnalysisSnapshot
from src.models_v3 import V3SnapshotEnvelope
from src.snapshots.v2_adapter import as_v2_artifact
from src.snapshots.v3_snapshot import persist_v3_snapshot, read_v3_snapshots


def test_same_ticker_and_date_coexist_without_changing_v2(tmp_path):
    now = datetime(2026, 9, 26, tzinfo=timezone.utc)
    v2 = AnalysisSnapshot(ticker="3702", market_date=date(2026, 9, 24), close=117.5,
        market_stage="TRANSITION", structure_state="DOWNTREND_STRUCTURE",
        bullish_evidence_count=1, bearish_evidence_count=1, warning_count=1,
        data_quality_status="PASS", created_at=now)
    version = version_record("404b40e", {"rules": "m1"}, created_at=now)
    v3 = V3SnapshotEnvelope(ticker="3702", market_date=v2.market_date,
        ruleset_version=version.ruleset_version, data_quality_status="PASS",
        payload={"foundation": True}, created_at=now)

    with connect(tmp_path / "coexist.duckdb") as db:
        persist_snapshots_and_events(db, "3702", [v2], [])
        before = read_snapshots(db, "3702")
        register_analysis_version(db, version)
        persist_v3_snapshot(db, v3)
        persist_v3_snapshot(db, v3)
        assert read_snapshots(db, "3702") == before
        assert as_v2_artifact(before[0]).analysis_version == "v2"
        assert read_v3_snapshots(db, "3702") == [v3]
        assert db.execute("SELECT count(*) FROM analysis_snapshots").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM snapshot_v3_daily").fetchone()[0] == 1
        with pytest.raises(ValueError, match="immutable"):
            persist_v3_snapshot(db, v3.model_copy(update={"payload": {"foundation": False}}))


def test_v3_snapshot_requires_registered_version(tmp_path):
    snapshot = V3SnapshotEnvelope(ticker="3702", market_date=date(2026, 9, 24),
        ruleset_version="m1-foundation", data_quality_status="PASS", created_at=datetime.now(timezone.utc))
    with connect(tmp_path / "unregistered.duckdb") as db:
        try:
            persist_v3_snapshot(db, snapshot)
        except ValueError as error:
            assert "registered" in str(error)
        else:
            raise AssertionError("unregistered V3 snapshot was persisted")
