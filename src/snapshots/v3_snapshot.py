from __future__ import annotations

import json

from src.models_v3 import V3SnapshotEnvelope


def persist_v3_snapshot(connection, snapshot: V3SnapshotEnvelope) -> None:
    registered = connection.execute(
        "SELECT 1 FROM analysis_versions WHERE analysis_version=? AND ruleset_version=?",
        [snapshot.analysis_version, snapshot.ruleset_version],
    ).fetchone()
    if registered is None:
        raise ValueError("V3 analysis version must be registered before snapshot persistence")
    payload_json = json.dumps(snapshot.payload, ensure_ascii=False, sort_keys=True, default=str)
    existing = connection.execute(
        "SELECT data_quality_status,payload_json,created_at FROM snapshot_v3_daily "
        "WHERE ticker=? AND market_date=? AND analysis_version=? AND ruleset_version=?",
        [snapshot.ticker, snapshot.market_date, snapshot.analysis_version, snapshot.ruleset_version],
    ).fetchone()
    identity = (snapshot.data_quality_status, payload_json)
    if existing is not None:
        if tuple(existing[:2]) != identity:
            raise ValueError("Persisted V3 snapshot is immutable for this version identity")
        return
    connection.execute(
        "INSERT INTO snapshot_v3_daily VALUES (?,?,?,?,?,?,?)",
        [snapshot.ticker, snapshot.market_date, snapshot.analysis_version, snapshot.ruleset_version,
         snapshot.data_quality_status, payload_json, snapshot.created_at],
    )


def read_v3_snapshots(connection, ticker: str, analysis_version: str = "v3") -> list[V3SnapshotEnvelope]:
    rows = connection.execute(
        "SELECT ticker,market_date,analysis_version,ruleset_version,data_quality_status,payload_json,created_at "
        "FROM snapshot_v3_daily WHERE ticker=? AND analysis_version=? ORDER BY market_date,ruleset_version",
        [ticker, analysis_version],
    ).fetchall()
    return [V3SnapshotEnvelope(ticker=row[0], market_date=row[1], analysis_version=row[2], ruleset_version=row[3],
        data_quality_status=row[4], payload=json.loads(row[5]), created_at=row[6]) for row in rows]
