from contextlib import contextmanager
from pathlib import Path
import json

import duckdb
import pandas as pd

from src.models import OHLCV, InstitutionalDaily, MarginDaily, PricePivot, PriceLevel, StructureSnapshot, Evidence, MarketStage

SCHEMA = """
CREATE TABLE IF NOT EXISTS ohlcv_daily (
 ticker VARCHAR, market_date DATE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
 volume BIGINT, turnover BIGINT, source VARCHAR, source_type VARCHAR, is_official BOOLEAN,
 retrieved_at TIMESTAMPTZ, volume_unit VARCHAR, turnover_unit VARCHAR, source_note VARCHAR,
 PRIMARY KEY(ticker, market_date));
CREATE TABLE IF NOT EXISTS data_quality_events (
 ticker VARCHAR, checked_at TIMESTAMPTZ DEFAULT current_timestamp,
 status VARCHAR, details_json VARCHAR);
CREATE TABLE IF NOT EXISTS institutional_daily (
 ticker VARCHAR, market_date DATE, foreign_net BIGINT, investment_trust_net BIGINT,
 dealer_net BIGINT, institutional_total_net BIGINT, source VARCHAR, source_type VARCHAR,
 is_official BOOLEAN, retrieved_at TIMESTAMPTZ, unit VARCHAR,
 PRIMARY KEY(ticker, market_date));
CREATE TABLE IF NOT EXISTS margin_daily (
 ticker VARCHAR, market_date DATE, margin_buy BIGINT, margin_sell BIGINT,
 margin_cash_repayment BIGINT, margin_balance BIGINT, short_sell BIGINT,
 short_cover BIGINT, short_stock_repayment BIGINT, short_balance BIGINT,
 source VARCHAR, source_type VARCHAR, is_official BOOLEAN, retrieved_at TIMESTAMPTZ,
 unit VARCHAR, source_note VARCHAR, PRIMARY KEY(ticker, market_date));
CREATE TABLE IF NOT EXISTS price_pivots (
 ticker VARCHAR, pivot_date DATE, confirmation_date DATE, pivot_kind VARCHAR, price DOUBLE,
 structure_label VARCHAR, comparison_date DATE, comparison_price DOUBLE, signal_type VARCHAR,
 annotation_type VARCHAR, PRIMARY KEY(ticker,pivot_date,pivot_kind));
CREATE TABLE IF NOT EXISTS structure_snapshots (
 ticker VARCHAR, market_date DATE, state VARCHAR, high_label VARCHAR, high_pivot_date DATE,
 high_price DOUBLE, low_label VARCHAR, low_pivot_date DATE, low_price DOUBLE,
 PRIMARY KEY(ticker,market_date));
CREATE TABLE IF NOT EXISTS price_levels (
 ticker VARCHAR, market_date DATE, level_type VARCHAR, rank INTEGER, price DOUBLE,
 derivation VARCHAR, evidence_date DATE, source_confirmation_date DATE,
 PRIMARY KEY(ticker,market_date,level_type,rank));
CREATE TABLE IF NOT EXISTS evidence_daily (
 ticker VARCHAR, market_date DATE, factor VARCHAR, status VARCHAR, headline VARCHAR,
 current_value VARCHAR, observations_json VARCHAR, reasoning VARCHAR, source_dates_json VARCHAR,
 updated_at TIMESTAMPTZ, PRIMARY KEY(ticker,market_date,factor));
CREATE TABLE IF NOT EXISTS market_stage_daily (
 ticker VARCHAR, market_date DATE, stage VARCHAR, reasons_json VARCHAR,
 evidence_factors_json VARCHAR, created_at TIMESTAMPTZ,
 PRIMARY KEY(ticker,market_date));
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
INSERT INTO schema_version VALUES (1) ON CONFLICT DO NOTHING;
INSERT INTO schema_version VALUES (2) ON CONFLICT DO NOTHING;
INSERT INTO schema_version VALUES (3) ON CONFLICT DO NOTHING;
INSERT INTO schema_version VALUES (4) ON CONFLICT DO NOTHING;
INSERT INTO schema_version VALUES (5) ON CONFLICT DO NOTHING;
"""


@contextmanager
def connect(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(path))
    try:
        connection.execute(SCHEMA)
        yield connection
    finally:
        connection.close()


def read_rows(connection, ticker: str) -> list[OHLCV]:
    cursor = connection.execute("SELECT * FROM ohlcv_daily WHERE ticker=? ORDER BY market_date", [ticker])
    names = [c[0] for c in cursor.description]
    return [OHLCV(**dict(zip(names, row))) for row in cursor.fetchall()]


def frame(rows: list[OHLCV]) -> pd.DataFrame:
    return pd.DataFrame([row.model_dump() for row in rows])


def read_typed_rows(connection, table, model, ticker):
    if table not in {"institutional_daily", "margin_daily"}:
        raise ValueError("Unsupported table")
    cursor = connection.execute(f"SELECT * FROM {table} WHERE ticker=? ORDER BY market_date", [ticker])
    names = [column[0] for column in cursor.description]
    return [model(**dict(zip(names, row))) for row in cursor.fetchall()]


def read_institutional(connection, ticker):
    return read_typed_rows(connection, "institutional_daily", InstitutionalDaily, ticker)


def read_margin(connection, ticker):
    return read_typed_rows(connection, "margin_daily", MarginDaily, ticker)


def _read_models(connection, query, params, model):
    cursor = connection.execute(query, params)
    names = [column[0] for column in cursor.description]
    return [model(**dict(zip(names, row))) for row in cursor.fetchall()]


def read_pivots(connection, ticker):
    return _read_models(connection, "SELECT * FROM price_pivots WHERE ticker=? ORDER BY confirmation_date,pivot_date", [ticker], PricePivot)


def read_levels(connection, ticker, market_date=None):
    if market_date is None:
        market_date = connection.execute("SELECT max(market_date) FROM price_levels WHERE ticker=?", [ticker]).fetchone()[0]
    return [] if market_date is None else _read_models(connection, "SELECT * FROM price_levels WHERE ticker=? AND market_date=? ORDER BY level_type,rank", [ticker, market_date], PriceLevel)


def read_structure(connection, ticker, market_date=None):
    if market_date is None:
        market_date = connection.execute("SELECT max(market_date) FROM structure_snapshots WHERE ticker=?", [ticker]).fetchone()[0]
    rows = [] if market_date is None else _read_models(connection, "SELECT * FROM structure_snapshots WHERE ticker=? AND market_date=?", [ticker, market_date], StructureSnapshot)
    return rows[0] if rows else None


def read_evidence(connection, ticker, market_date=None):
    if market_date is None:
        market_date = connection.execute("SELECT max(market_date) FROM evidence_daily WHERE ticker=?", [ticker]).fetchone()[0]
    if market_date is None:
        return []
    cursor = connection.execute("SELECT * FROM evidence_daily WHERE ticker=? AND market_date=? ORDER BY factor", [ticker, market_date])
    names = [column[0] for column in cursor.description]
    result = []
    for row in cursor.fetchall():
        item = dict(zip(names, row))
        item["observations"] = json.loads(item.pop("observations_json"))
        item["source_dates"] = json.loads(item.pop("source_dates_json"))
        result.append(Evidence(**item))
    return result


def read_market_stage(connection, ticker, market_date=None):
    if market_date is None:
        market_date = connection.execute("SELECT max(market_date) FROM market_stage_daily WHERE ticker=?", [ticker]).fetchone()[0]
    if market_date is None:
        return None
    cursor = connection.execute("SELECT * FROM market_stage_daily WHERE ticker=? AND market_date=?", [ticker, market_date])
    names, row = [column[0] for column in cursor.description], cursor.fetchone()
    if row is None:
        return None
    item = dict(zip(names, row))
    item["reasons"] = json.loads(item.pop("reasons_json"))
    item["evidence_factors"] = json.loads(item.pop("evidence_factors_json"))
    return MarketStage(**item)


def persist(connection, rows, quality):
    if quality.status == "FAIL":
        raise ValueError("Validation FAIL prevents persistence and indicator calculation")
    records = frame(rows)
    connection.register("incoming", records)
    connection.execute("BEGIN TRANSACTION")
    try:
        connection.execute("INSERT OR REPLACE INTO ohlcv_daily SELECT * FROM incoming")
        record_quality(connection, rows[0].ticker, quality)
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.unregister("incoming")


def persist_phase2(connection, institutional, margin, quality):
    if quality.status == "FAIL":
        raise ValueError("Phase 2 validation FAIL prevents persistence")
    inst_frame, margin_frame = frame(institutional), frame(margin)
    connection.register("incoming_institutional", inst_frame)
    connection.register("incoming_margin", margin_frame)
    connection.execute("BEGIN TRANSACTION")
    try:
        connection.execute("INSERT OR REPLACE INTO institutional_daily SELECT * FROM incoming_institutional")
        connection.execute("INSERT OR REPLACE INTO margin_daily SELECT * FROM incoming_margin")
        record_quality(connection, institutional[0].ticker, quality)
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.unregister("incoming_institutional")
        connection.unregister("incoming_margin")


def persist_phase3(connection, ticker, pivots, snapshots, levels):
    frames = {"incoming_pivots": frame(pivots), "incoming_snapshots": frame(snapshots), "incoming_levels": frame(levels)}
    for name, records in frames.items():
        connection.register(name, records)
    connection.execute("BEGIN TRANSACTION")
    try:
        for table in ("price_pivots", "structure_snapshots", "price_levels"):
            connection.execute(f"DELETE FROM {table} WHERE ticker=?", [ticker])
        connection.execute("INSERT INTO price_pivots SELECT * FROM incoming_pivots")
        connection.execute("INSERT INTO structure_snapshots SELECT * FROM incoming_snapshots")
        connection.execute("INSERT INTO price_levels SELECT * FROM incoming_levels")
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        for name in frames:
            connection.unregister(name)


def persist_evidence(connection, ticker, evidence):
    records = pd.DataFrame([{
        **item.model_dump(exclude={"observations", "source_dates"}),
        "observations_json": json.dumps(item.observations, ensure_ascii=False, default=str),
        "source_dates_json": json.dumps(item.source_dates, default=str),
    } for item in evidence])
    records = records[["ticker","market_date","factor","status","headline","current_value","observations_json","reasoning","source_dates_json","updated_at"]]
    connection.register("incoming_evidence", records)
    connection.execute("BEGIN TRANSACTION")
    try:
        connection.execute("DELETE FROM evidence_daily WHERE ticker=?", [ticker])
        connection.execute("INSERT INTO evidence_daily SELECT * FROM incoming_evidence")
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.unregister("incoming_evidence")


def persist_market_stages(connection, ticker, stages):
    records = pd.DataFrame([{
        **item.model_dump(exclude={"reasons", "evidence_factors"}),
        "reasons_json": json.dumps(item.reasons, ensure_ascii=False),
        "evidence_factors_json": json.dumps(item.evidence_factors, ensure_ascii=False),
    } for item in stages])
    records = records[["ticker","market_date","stage","reasons_json","evidence_factors_json","created_at"]]
    connection.register("incoming_stages", records)
    connection.execute("BEGIN TRANSACTION")
    try:
        connection.execute("DELETE FROM market_stage_daily WHERE ticker=?", [ticker])
        connection.execute("INSERT INTO market_stage_daily SELECT * FROM incoming_stages")
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.unregister("incoming_stages")


def record_quality(connection, ticker, quality):
    connection.execute("INSERT INTO data_quality_events(ticker,status,details_json) VALUES (?,?,?)",
                       [ticker, quality.status, quality.model_dump_json()])
