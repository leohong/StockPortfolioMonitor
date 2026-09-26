from __future__ import annotations

import argparse
from datetime import date

import httpx
import pandas as pd

from src.analysis.regime.market_regime import calculate_market_regimes
from src.analysis.versioning import V3_RULESET_VERSION, register_analysis_version, version_record
from src.config import load_config
from src.data.benchmark_normalizer import normalize_sector_classification, normalize_taiex
from src.data.providers.twse_benchmark import fetch_sector_classification, fetch_taiex_month
from src.database.db import connect
from src.database.v3 import persist_benchmark, persist_regimes, persist_sector_classifications, read_benchmark, read_regime, read_sector_as_of
from src.models_v3 import RegimeEvidence
from src.services.stock_service import months, taipei_today


def _validate_benchmark(rows):
    dates = [row.market_date for row in rows]
    if not rows or len(dates) != len(set(dates)):
        raise ValueError("TAIEX benchmark is empty or contains duplicate dates")
    for row in rows:
        if not row.is_official or row.low > min(row.open, row.close) or row.high < max(row.open, row.close):
            raise ValueError(f"Invalid official TAIEX OHLC on {row.market_date}")
        if row.volume < 0 or row.turnover < 0:
            raise ValueError(f"Invalid official TAIEX market totals on {row.market_date}")


def _insufficient_sector(ticker: str, market_date, reason: str) -> RegimeEvidence:
    from datetime import datetime, timezone
    return RegimeEvidence(context_type="SECTOR", context_id=ticker, market_date=market_date,
        regime="INSUFFICIENT_DATA", confidence_class="INSUFFICIENT", missing_inputs=[reason],
        source_dates=[], ruleset_version=V3_RULESET_VERSION, created_at=datetime.now(timezone.utc))


def refresh_regimes(settings, tickers: list[str], git_commit: str, as_of: date | None = None, full: bool = False):
    as_of = as_of or taipei_today()
    offset = as_of.year * 12 + as_of.month - settings.history_months
    start = date(offset // 12, offset % 12 + 1, 1)
    collected = []
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for month in months(start, as_of):
            collected.extend(normalize_taiex(fetch_taiex_month(month, settings.cache_dir, client, force=full)))
        classifications = normalize_sector_classification(
            fetch_sector_classification(settings.cache_dir, client, force=full), set(tickers))
    collected = [row for row in collected if row.market_date <= as_of]
    _validate_benchmark(collected)
    version = version_record(git_commit, settings)
    with connect(settings.database) as db:
        persist_benchmark(db, collected)
        persist_sector_classifications(db, classifications)
        benchmark = read_benchmark(db)
        benchmark = benchmark[pd.to_datetime(benchmark.market_date).dt.date <= as_of]
        regimes = calculate_market_regimes(benchmark, version.ruleset_version)
        register_analysis_version(db, version)
        persist_regimes(db, regimes)
        latest_date = regimes[-1].market_date
        sector_regimes = []
        for ticker in tickers:
            classification = read_sector_as_of(db, ticker, latest_date)
            reason = "sector_classification_as_of" if classification is None else "sector_benchmark"
            sector_regimes.append(_insufficient_sector(ticker, latest_date, reason))
        persist_regimes(db, sector_regimes)
    return regimes[-1], sector_regimes


def load_regime_context(settings, ticker: str, as_of):
    with connect(settings.database) as db:
        market = read_regime(db, "MARKET", "TAIEX", as_of)
        sector = read_regime(db, "SECTOR", ticker, as_of)
        classification = read_sector_as_of(db, ticker, as_of)
    return market, sector, classification


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    settings, holdings, _ = load_config()
    market, sectors = refresh_regimes(settings, [item.ticker for item in holdings], args.git_commit, full=args.full)
    print(market.model_dump_json(indent=2))
    print("\n".join(item.model_dump_json(indent=2) for item in sectors))
