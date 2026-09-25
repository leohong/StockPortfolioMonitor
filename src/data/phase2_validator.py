from datetime import date

from src.models import InstitutionalDaily, MarginDaily, QualityResult


def validate_phase2(institutional: list[InstitutionalDaily], margin: list[MarginDaily],
                    expected_dates: set[date]) -> QualityResult:
    errors = []
    for name, rows, unit in (("institutional", institutional, "shares"), ("margin", margin, "trading_units")):
        dates = [row.market_date for row in rows]
        if len(dates) != len(set(dates)):
            errors.append(f"{name}: duplicate market dates")
        if dates != sorted(dates):
            errors.append(f"{name}: market dates not ordered")
        missing = sorted(expected_dates - set(dates))
        extra = sorted(set(dates) - expected_dates)
        if missing:
            errors.append(f"{name}: missing OHLCV dates: {', '.join(map(str, missing[:10]))}")
        if extra:
            errors.append(f"{name}: dates absent from OHLCV: {', '.join(map(str, extra[:10]))}")
        for row in rows:
            if row.unit != unit or not row.is_official or not row.source.startswith("https://www.twse.com.tw/"):
                errors.append(f"{name} {row.market_date}: invalid unit or provenance")
            if row.retrieved_at.tzinfo is None:
                errors.append(f"{name} {row.market_date}: retrieval timestamp lacks timezone")
    for row in institutional:
        if row.foreign_net + row.investment_trust_net + row.dealer_net != row.institutional_total_net:
            errors.append(f"institutional {row.market_date}: participant nets do not equal total")
    return QualityResult(status="FAIL" if errors else "PASS", errors=errors)
