from __future__ import annotations

import json

import pandas as pd

from src.models_v3 import BenchmarkDaily, MomentumState, RegimeEvidence, RelativeStrengthState, SectorClassification, TrendQuality


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


def _persist_versioned_rows(connection, table, rows, columns, json_fields):
    for item in rows:
        values = item.model_dump()
        for field in json_fields:
            values[f"{field}_json"] = json.dumps(values.pop(field), ensure_ascii=False, sort_keys=True, default=str)
        identity = [item.ticker, item.market_date, item.analysis_version, item.ruleset_version]
        existing = connection.execute(
            f"SELECT {','.join(columns)} FROM {table} WHERE ticker=? AND market_date=? AND analysis_version=? AND ruleset_version=?",
            identity,
        ).fetchone()
        payload = tuple(values[column] for column in columns)
        if existing is not None:
            # created_at is provenance rather than analytical content.
            comparable = [index for index,column in enumerate(columns) if column != "created_at"]
            if any(existing[index] != payload[index] for index in comparable):
                raise ValueError(f"Persisted {table} row is immutable for this version identity")
            continue
        placeholders = ",".join("?" for _ in columns)
        connection.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})", list(payload))


def persist_trend_quality(connection, rows: list[TrendQuality]):
    columns = ["ticker","market_date","state","ma5","ma20","ma60","ma120","ma20_slope_5d_pct",
        "ma60_slope_5d_pct","ma120_slope_5d_pct","distance_ma20_pct","distance_ma60_pct",
        "ma20_ma60_separation_pct","persistence_20d","observations_json","source_dates_json",
        "analysis_version","ruleset_version","created_at"]
    _persist_versioned_rows(connection, "trend_quality_daily", rows, columns, ("observations","source_dates"))


def persist_momentum_states(connection, rows: list[MomentumState]):
    columns = ["ticker","market_date","state","rsi14","rsi_change_5d","roc20","rsi_cross","divergence",
        "divergence_pivot_date","divergence_confirmation_date","observations_json","source_dates_json",
        "analysis_version","ruleset_version","created_at"]
    _persist_versioned_rows(connection, "momentum_state_daily", rows, columns, ("observations","source_dates"))


def persist_relative_strength(connection, rows: list[RelativeStrengthState]):
    columns = ["ticker","market_date","benchmark_symbol","benchmark_date","rs_line","rs_line_indexed",
        "rs_market_20d","rs_market_60d","rs_market_120d","rs_line_change_20d","state","rs_sector_20d",
        "sector_state","missing_inputs_json","price_basis","corporate_action_warning","source_dates_json",
        "analysis_version","ruleset_version","created_at"]
    _persist_versioned_rows(connection, "relative_strength_daily", rows, columns, ("missing_inputs","source_dates"))


def read_latest_m3(connection, ticker: str, as_of=None):
    result = {}
    for name, table in (("trend","trend_quality_daily"),("momentum","momentum_state_daily"),("relative_strength","relative_strength_daily")):
        clause, params = "ticker=?", [ticker]
        if as_of is not None:
            clause += " AND market_date<=?"; params.append(as_of)
        cursor = connection.execute(f"SELECT * FROM {table} WHERE {clause} ORDER BY market_date DESC,created_at DESC LIMIT 1", params)
        names, row = [column[0] for column in cursor.description], cursor.fetchone()
        result[name] = None if row is None else dict(zip(names,row))
    return result
