from datetime import date

import pandas as pd

from src.analysis.price_structure import detect_pivots, derive_levels, structure_snapshot


def sample():
    highs = [2,3,5,3,2,4,6,4,3,5,7,5,4]
    lows = [1,2,3,2,1,3,4,3,2,4,5,4,3]
    dates = pd.date_range("2026-01-01", periods=len(highs), freq="D")
    return pd.DataFrame({"ticker":"3702", "market_date":dates.date, "open":lows, "high":highs,
        "low":lows, "close":[(a+b)/2 for a,b in zip(highs,lows)], "ma20":[None]*len(highs),
        "ma60":[None]*len(highs), "volume_ratio_20":[1]*len(highs)})


def test_confirmed_pivots_have_evidence_and_classification():
    pivots = detect_pivots(sample(), 2, 2)
    assert [(p.pivot_date, p.confirmation_date, p.structure_label) for p in pivots] == [
        (date(2026,1,3), date(2026,1,5), None), (date(2026,1,5), date(2026,1,7), None),
        (date(2026,1,7), date(2026,1,9), "HH"), (date(2026,1,9), date(2026,1,11), "HL"),
        (date(2026,1,11), date(2026,1,13), "HH")]
    assert pivots[2].comparison_date == date(2026,1,3)
    assert pivots[2].comparison_price == 5
    assert pivots[2].signal_type == "REAL_TIME_SIGNAL"
    assert pivots[2].annotation_type == "RETROSPECTIVE_ANNOTATION"


def test_no_lookahead_prefix_matches_full_history():
    data, cutoff = sample(), date(2026,1,9)
    full_known = [p.model_dump() for p in detect_pivots(data, 2, 2) if p.confirmation_date <= cutoff]
    prefix = [p.model_dump() for p in detect_pivots(data, 2, 2, cutoff)]
    assert prefix == full_known
    assert all(p["pivot_date"] != date(2026,1,9) for p in prefix)


def test_structure_and_role_reversal_levels_use_confirmed_data_only():
    data = sample(); pivots = detect_pivots(data, 2, 2)
    snapshot = structure_snapshot("3702", date(2026,1,13), pivots)
    assert snapshot.state == "UPTREND_STRUCTURE"
    data.loc[data.index[-1], "close"] = 8
    levels = derive_levels(data, pivots, date(2026,1,13), 1)
    assert all(x.source_confirmation_date is None or x.source_confirmation_date <= x.market_date for x in levels)
    assert any(x.derivation == "壓力突破後轉為支撐" for x in levels)
    assert {x.rank for x in levels if x.level_type == "SUPPORT"} <= {1,2}


def test_configurable_sensitivity_changes_pivots():
    assert len(detect_pivots(sample(), 1, 1)) >= len(detect_pivots(sample(), 3, 3))
