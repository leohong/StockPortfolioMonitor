from datetime import date

import pytest

from src.data.validator import validate
from src.data.normalizer import normalize

AS_OF = date(2026, 8, 31)


def test_valid_real_data_warns_about_unadjusted_actions(real_rows):
    result = validate(real_rows, AS_OF)
    assert result.status == "PASS_WITH_WARNINGS"
    assert not result.errors
    assert any("2026-08-27" in w and "adjustment" in w for w in result.warnings)


@pytest.mark.parametrize("field,value", [("open", 1000), ("close", 0), ("low", float('nan')), ("high", None), ("volume", -1), ("turnover", -1), ("volume_unit", "lots"), ("is_official", False)])
def test_invalid_data_fails(real_rows, field, value):
    real_rows[0] = real_rows[0].model_copy(update={field: value})
    assert validate(real_rows, AS_OF).status == "FAIL"


def test_duplicate_order_future_and_empty(real_rows):
    assert validate(real_rows + [real_rows[0]], AS_OF).status == "FAIL"
    assert validate(list(reversed(real_rows)), AS_OF).status == "FAIL"
    assert validate(real_rows, date(2026, 8, 10)).status == "FAIL"
    assert validate([], AS_OF).status == "FAIL"


def test_staleness_and_missing_sessions(real_rows):
    check = validate(real_rows, date(2026, 9, 20), expected_sessions={date(2026, 8, 1)})
    assert any("Stale" in w for w in check.warnings)
    assert any("Missing expected sessions" in w for w in check.warnings)


def test_missing_price_not_filled(envelope):
    envelope["payload"]["data"][0][3] = "--"
    rows = normalize("3702", envelope)
    assert rows[0].open is None
    assert validate(rows, AS_OF).status == "FAIL"


def test_schema_drift_rejected(envelope):
    envelope["payload"]["fields"][1] = "成交張數"
    with pytest.raises(ValueError, match="schema"):
        normalize("3702", envelope)
