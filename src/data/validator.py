import math
from datetime import date

from src.models import OHLCV, QualityResult


def validate(rows: list[OHLCV], as_of: date, stale_days: int = 7, expected_sessions: set[date] | None = None) -> QualityResult:
    errors, warnings = [], []
    if not rows:
        return QualityResult(status="FAIL", errors=["No OHLCV rows"])
    dates = [r.market_date for r in rows]
    if len(set(dates)) != len(dates):
        errors.append("Duplicate market dates")
    if dates != sorted(dates):
        errors.append("Market dates not ordered")
    if len({r.ticker for r in rows}) != 1:
        errors.append("Mixed tickers")
    for r in rows:
        tag = r.market_date.isoformat()
        if r.market_date > as_of:
            errors.append(f"{tag}: future market date")
        values = [r.open, r.high, r.low, r.close]
        if any(v is None or not math.isfinite(v) or v <= 0 for v in values):
            errors.append(f"{tag}: missing/nonfinite/nonpositive OHLC")
        elif not (r.low <= r.open <= r.high and r.low <= r.close <= r.high):
            errors.append(f"{tag}: invalid OHLC bounds")
        if r.volume is None or r.volume < 0 or r.turnover is None or r.turnover < 0:
            errors.append(f"{tag}: invalid volume/turnover")
        elif r.volume == 0:
            warnings.append(f"{tag}: zero volume; confirm trading status")
        if r.volume_unit != "shares" or r.turnover_unit != "TWD":
            errors.append(f"{tag}: unknown units")
        if not r.is_official or not r.source.startswith("https://www.twse.com.tw/") or r.retrieved_at.tzinfo is None:
            errors.append(f"{tag}: invalid provenance")
        if "X" in r.source_note or "**" in r.source_note:
            warnings.append(f"{tag}: source marks ex-right/dividend or price adjustment; raw unadjusted series")
    if (as_of - max(dates)).days > stale_days:
        warnings.append(f"Stale data: latest session {max(dates)}")
    for previous, current in zip(rows, rows[1:]):
        if previous.close and current.close and abs(current.close / previous.close - 1) > 0.11:
            warnings.append(f"{current.market_date}: suspicious price discontinuity (>11%); review corporate actions")
    if expected_sessions is None:
        warnings.append("Missing sessions unverified: official exchange calendar not integrated; holidays are not fabricated")
    elif missing := sorted(expected_sessions - set(dates)):
        warnings.append(f"Missing expected sessions: {', '.join(map(str, missing))}")
    warnings.append("Corporate actions not fully verified (dividends, splits, capital reductions/increases); prices are unadjusted")
    warnings.append("Single official source: cross-source conflicts not independently checked")
    return QualityResult(status="FAIL" if errors else "PASS_WITH_WARNINGS" if warnings else "PASS", errors=errors, warnings=warnings)
