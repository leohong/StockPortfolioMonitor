from __future__ import annotations

import json

import pandas as pd

from src.models_v3 import BenchmarkDaily, RegimeEvidence, SectorClassification


def persist_benchmark(connection, rows: list[BenchmarkDaily]) -> None:
    if not rows:
        return
    records = pd.DataFrame([row.model_dump() for row in rows])
    connection.register("incoming_benchmark", records)
    try:
        connection.execute("INSERT OR REPLACE INTO benchmark_daily SELECT * FROM incoming_benchmark")
    finally:
        connection.unregister("incoming_benchmark")


def read_benchmark(connection, symbol: str = "TAIEX") -> pd.DataFrame:
    return connection.execute("SELECT * FROM benchmark_daily WHERE symbol=? ORDER BY market_date", [symbol]).fetchdf()


def persist_sector_classifications(connection, rows: list[SectorClassification]) -> None:
    if not rows:
        return
    records = pd.DataFrame([row.model_dump() for row in rows])
    connection.register("incoming_classifications", records)
    try:
        connection.execute("INSERT OR REPLACE INTO sector_classification SELECT * FROM incoming_classifications")
    finally:
        connection.unregister("incoming_classifications")


def read_sector_as_of(connection, ticker: str, as_of):
    return connection.execute(
        "SELECT * FROM sector_classification WHERE ticker=? AND effective_from<=? AND available_date<=? "
        "AND (effective_to IS NULL OR effective_to>=?) ORDER BY effective_from DESC LIMIT 1",
        [ticker, as_of, as_of, as_of],
    ).fetchone()


def persist_regimes(connection, regimes: list[RegimeEvidence]) -> None:
    for item in regimes:
        values = [json.dumps(value, ensure_ascii=False, sort_keys=True, default=str) for value in
                  (item.evidence_for, item.evidence_against, item.missing_inputs, item.source_dates)]
        identity = [item.context_type, item.context_id, item.market_date, item.analysis_version, item.ruleset_version]
        existing = connection.execute(
            "SELECT regime,confidence_class,evidence_for_json,evidence_against_json,missing_inputs_json,source_dates_json "
            "FROM regime_daily WHERE context_type=? AND context_id=? AND market_date=? AND analysis_version=? AND ruleset_version=?",
            identity,
        ).fetchone()
        payload = (item.regime, item.confidence_class, *values)
        if existing is not None:
            if tuple(existing) != payload:
                raise ValueError("Persisted regime is immutable for this version identity")
            continue
        connection.execute("INSERT INTO regime_daily VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [item.context_type, item.context_id, item.market_date, item.regime, item.confidence_class,
             *values, item.analysis_version, item.ruleset_version, item.created_at])


def read_regime(connection, context_type: str, context_id: str, as_of=None) -> RegimeEvidence | None:
    clause, params = "context_type=? AND context_id=?", [context_type, context_id]
    if as_of is not None:
        clause += " AND market_date<=?"; params.append(as_of)
    cursor = connection.execute(f"SELECT * FROM regime_daily WHERE {clause} ORDER BY market_date DESC LIMIT 1", params)
    names, row = [column[0] for column in cursor.description], cursor.fetchone()
    if row is None:
        return None
    item = dict(zip(names, row))
    for field in ("evidence_for", "evidence_against", "missing_inputs", "source_dates"):
        item[field] = json.loads(item.pop(f"{field}_json"))
    return RegimeEvidence(**item)
