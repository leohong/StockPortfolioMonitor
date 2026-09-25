import argparse
from datetime import date
from zoneinfo import ZoneInfo
from datetime import datetime

from src.config import load_config
from src.data.normalizer import normalize
from src.data.providers.twse import fetch_month
from src.data.validator import validate
from src.database.db import connect, read_rows, persist, record_quality, frame
from src.indicators.core import calculate
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
    quality = validate(rows, as_of or taipei_today(), settings.stale_days)
    if quality.status == "FAIL":
        return frame(rows), quality
    return calculate(frame(rows)), quality


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="3702")
    parser.add_argument("--full", action="store_true", help="Re-fetch configured history to review older source revisions")
    args = parser.parse_args()
    configure_logging()
    settings, _, _ = load_config()
    print(refresh(settings, args.ticker, full=args.full).model_dump_json(indent=2))
