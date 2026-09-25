import argparse
import httpx
import time
from datetime import date
from zoneinfo import ZoneInfo
from datetime import datetime

from src.config import load_config
from src.data.normalizer import normalize
from src.data.providers.twse import fetch_month
from src.data.validator import validate
from src.data.phase2_normalizer import normalize_institutional, normalize_margin
from src.data.phase2_validator import validate_phase2
from src.data.providers.twse_phase2 import fetch_daily
from src.database.db import (connect, read_rows, persist, record_quality, frame,
                             read_institutional, read_margin, persist_phase2)
from src.indicators.core import calculate
from src.analysis.phase2_metrics import calculate_phase2
from src.logging_config import event, configure_logging


def taipei_today():
    return datetime.now(ZoneInfo("Asia/Taipei")).date()


def months(start: date, end: date):
    cursor = start.replace(day=1)
    while cursor <= end:
        yield cursor
        cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)


def refresh(settings, ticker: str, as_of: date | None = None, full: bool = False):
    as_of = as_of or taipei_today()
    with connect(settings.database) as db:
        existing = read_rows(db, ticker)
    # Re-fetch latest stored month to recover partial months and source revisions.
    offset = as_of.year * 12 + as_of.month - settings.history_months
    start = date(offset // 12, offset % 12 + 1, 1)
    if existing and not full:
        start = existing[-1].market_date.replace(day=1)
    collected = []
    try:
        for month in months(start, as_of):
            rows = normalize(ticker, fetch_month(ticker, month, settings.cache_dir))
            if any(row.market_date.year != month.year or row.market_date.month != month.month for row in rows):
                raise ValueError("Source returned dates outside requested month")
            rows = [r for r in rows if r.market_date <= as_of]
            check = validate(rows, as_of, settings.stale_days)
            if check.status == "FAIL":
                event("VALIDATION_FAIL", ticker=ticker, errors=check.errors)
                with connect(settings.database) as db:
                    record_quality(db, ticker, check)
                raise ValueError("; ".join(check.errors))
            collected.extend(rows)
        combined = {r.market_date: r for r in existing}
        conflicts = []
        for row in collected:
            old = combined.get(row.market_date)
            if old and any(getattr(old, f) != getattr(row, f) for f in ("open", "high", "low", "close", "volume", "turnover")):
                conflicts.append(f"Official source revision {row.market_date}: old={old.model_dump_json()} new={row.model_dump_json()}")
            combined[row.market_date] = row
        merged = sorted(combined.values(), key=lambda r: r.market_date)
        quality = validate(merged, as_of, settings.stale_days)
        quality.warnings.extend(conflicts)
        if conflicts and quality.status == "PASS":
            quality.status = "PASS_WITH_WARNINGS"
        with connect(settings.database) as db:
            persist(db, merged, quality)
        event("VALIDATION_WARNING" if quality.warnings else "ANALYSIS_COMPLETE", ticker=ticker, status=quality.status, rows=len(merged))
        return quality
    except Exception as exc:
        event("DATA_FETCH_FAIL", ticker=ticker, error=str(exc))
        raise


def load_stock(settings, ticker, as_of=None):
    with connect(settings.database) as db:
        rows = read_rows(db, ticker)
        institutional = read_institutional(db, ticker)
        margin = read_margin(db, ticker)
    quality = validate(rows, as_of or taipei_today(), settings.stale_days)
    if quality.status == "FAIL":
        return frame(rows), quality
    result = calculate(frame(rows))
    if institutional and margin:
        inst, mar = calculate_phase2(frame(institutional), frame(margin))
        result = result.merge(inst, on=["ticker", "market_date"], how="left", suffixes=("", "_institutional"))
        result = result.merge(mar, on=["ticker", "market_date"], how="left", suffixes=("", "_margin"))
    return result, quality


def refresh_phase2(settings, ticker: str, full: bool = False, limit: int = 250):
    with connect(settings.database) as db:
        ohlcv = read_rows(db, ticker)
        existing_inst = read_institutional(db, ticker)
        existing_margin = read_margin(db, ticker)
    if len(ohlcv) < limit:
        raise ValueError(f"Need at least {limit} validated OHLCV sessions before Phase 2; got {len(ohlcv)}")
    target_dates = [row.market_date for row in ohlcv[-limit:]]
    inst_by_date = {} if full else {row.market_date: row for row in existing_inst if row.market_date in target_dates}
    margin_by_date = {} if full else {row.market_date: row for row in existing_margin if row.market_date in target_dates}
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            for index, market_date in enumerate(target_dates, 1):
                if market_date not in inst_by_date:
                    inst_by_date[market_date] = normalize_institutional(
                        ticker, market_date, fetch_daily("institutional", market_date, settings.cache_dir, client, force=full))
                if market_date not in margin_by_date:
                    margin_by_date[market_date] = normalize_margin(
                        ticker, market_date, fetch_daily("margin", market_date, settings.cache_dir, client, force=full))
                time.sleep(0.20)
                if index % 25 == 0:
                    event("DATA_FETCH_PROGRESS", ticker=ticker, completed=index, total=len(target_dates))
        institutional = [inst_by_date[day] for day in target_dates]
        margin = [margin_by_date[day] for day in target_dates]
        quality = validate_phase2(institutional, margin, set(target_dates))
        if quality.status == "FAIL":
            event("VALIDATION_FAIL", ticker=ticker, dataset="phase2", errors=quality.errors)
            raise ValueError("; ".join(quality.errors))
        with connect(settings.database) as db:
            persist_phase2(db, institutional, margin, quality)
        event("ANALYSIS_COMPLETE", ticker=ticker, dataset="phase2", rows=len(target_dates))
        return quality
    except Exception as exc:
        event("DATA_FETCH_FAIL", ticker=ticker, dataset="phase2", error=str(exc))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="3702")
    parser.add_argument("--full", action="store_true", help="Re-fetch configured history to review older source revisions")
    parser.add_argument("--phase2", action="store_true", help="Fetch official institutional and margin data")
    args = parser.parse_args()
    configure_logging()
    settings, _, _ = load_config()
    action = refresh_phase2 if args.phase2 else refresh
    print(action(settings, args.ticker, full=args.full).model_dump_json(indent=2))
