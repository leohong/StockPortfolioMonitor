from datetime import date

import pytest

from src.config import load_config
from src.database.db import connect, read_rows, persist
from src.data.validator import validate
from src.models import QualityResult
from src.services.stock_service import refresh, load_stock


def test_database_roundtrip_idempotence_and_gate(tmp_path, real_rows):
    path = tmp_path / "stocks.duckdb"
    quality = validate(real_rows, date(2026, 8, 31))
    with connect(path) as db:
        persist(db, real_rows, quality)
        persist(db, real_rows, quality)
        assert read_rows(db, "3702") == real_rows
        with pytest.raises(ValueError, match="FAIL"):
            persist(db, real_rows, QualityResult(status="FAIL"))


def test_incremental_refresh_and_failure_preserves_data(tmp_path, real_rows, envelope, monkeypatch):
    settings, _, _ = load_config()
    settings.database = tmp_path / "db.duckdb"
    settings.cache_dir = tmp_path / "cache"
    with connect(settings.database) as db:
        persist(db, real_rows, validate(real_rows, date(2026, 8, 31)))
    requested = []
    def fetch(ticker, month, cache):
        requested.append(month)
        return envelope
    monkeypatch.setattr("src.services.stock_service.fetch_month", fetch)
    refresh(settings, "3702", date(2026, 8, 31))
    assert requested == [date(2026, 8, 1)]
    before, _ = load_stock(settings, "3702", date(2026, 8, 31))
    def unavailable(*args):
        raise ValueError("official source unavailable")
    monkeypatch.setattr("src.services.stock_service.fetch_month", unavailable)
    with pytest.raises(ValueError, match="unavailable"):
        refresh(settings, "3702", date(2026, 9, 25))
    after, _ = load_stock(settings, "3702", date(2026, 8, 31))
    assert before.equals(after)
