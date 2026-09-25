from contextlib import contextmanager
from pathlib import Path

import duckdb
import pandas as pd

from src.models import OHLCV, InstitutionalDaily, MarginDaily

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
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
INSERT INTO schema_version VALUES (1) ON CONFLICT DO NOTHING;
INSERT INTO schema_version VALUES (2) ON CONFLICT DO NOTHING;
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


def record_quality(connection, ticker, quality):
    connection.execute("INSERT INTO data_quality_events(ticker,status,details_json) VALUES (?,?,?)",
                       [ticker, quality.status, quality.model_dump_json()])
