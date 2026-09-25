from contextlib import contextmanager
from pathlib import Path

import duckdb
import pandas as pd

from src.models import OHLCV

SCHEMA = """
CREATE TABLE IF NOT EXISTS ohlcv_daily (
 ticker VARCHAR, market_date DATE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
 volume BIGINT, turnover BIGINT, source VARCHAR, source_type VARCHAR, is_official BOOLEAN,
 retrieved_at TIMESTAMPTZ, volume_unit VARCHAR, turnover_unit VARCHAR, source_note VARCHAR,
 PRIMARY KEY(ticker, market_date));
CREATE TABLE IF NOT EXISTS data_quality_events (
 ticker VARCHAR, checked_at TIMESTAMPTZ DEFAULT current_timestamp,
 status VARCHAR, details_json VARCHAR);
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
INSERT INTO schema_version VALUES (1) ON CONFLICT DO NOTHING;
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


def record_quality(connection, ticker, quality):
    connection.execute("INSERT INTO data_quality_events(ticker,status,details_json) VALUES (?,?,?)",
                       [ticker, quality.status, quality.model_dump_json()])
