from datetime import date
from types import SimpleNamespace

from src.analysis.market_stage import classify_stage
from src.models import Evidence, StructureSnapshot


def row(**changes):
    values = dict(ticker="3702", market_date=date(2026,9,24), close=120, ma5=116, ma20=110,
                  rsi14=65, volume_ratio_20=1.0, margin_change_pct_20d=5, foreign_5d=100)
    values.update(changes)
    return SimpleNamespace(**values)


def structure(state="UPTREND_STRUCTURE", high="HH", low="HL"):
    return StructureSnapshot(ticker="3702", market_date=date(2026,9,24), state=state,
        high_label=high, high_pivot_date=date(2026,9,18), high_price=122,
        low_label=low, low_pivot_date=date(2026,9,10), low_price=108)


def evidence():
    return [Evidence(ticker="3702", market_date=date(2026,9,24), factor="rsi", status="BULLISH",
        headline="RSI", current_value="65", reasoning="test", source_dates=[date(2026,9,24)],
        updated_at="2026-09-24T00:00:00Z")]


def test_deterministic_uptrend_and_reason_list():
    actual = classify_stage(row(), structure(), evidence(), row(ma20=109), "C_BASE_CONFIRMATION")
    repeated = classify_stage(row(), structure(), evidence(), row(ma20=109), "C_BASE_CONFIRMATION")
    assert actual.stage == repeated.stage == "D_UPTREND"
    assert actual.reasons == repeated.reasons
    assert "price" not in actual.evidence_factors
    assert len(actual.reasons) == 3


def test_transition_overheated_to_high_level_correction():
    hot = classify_stage(row(close=130, rsi14=76, volume_ratio_20=1.5), structure(), evidence(), row(ma20=109), "D_UPTREND")
    assert hot.stage == "E_OVERHEATED"
    correction = classify_stage(row(close=111, ma5=115, rsi14=64), structure(), evidence(), row(ma20=110), hot.stage)
    assert correction.stage == "F_HIGH_LEVEL_CORRECTION"
    assert "前一交易日為過熱階段" in correction.reasons


def test_early_base_to_base_confirmation_transition():
    base = structure("POSSIBLE_BASE", "LH", "HL")
    early = classify_stage(row(close=108, ma5=110, ma20=112, rsi14=44), base, evidence(), row(rsi14=40), "A_DOWNTREND")
    assert early.stage == "B_EARLY_BASE"
    confirmed = classify_stage(row(close=114, ma5=111, ma20=112, rsi14=54), base, evidence(), row(rsi14=49), early.stage)
    assert confirmed.stage == "C_BASE_CONFIRMATION"
    assert any("HL" in reason for reason in confirmed.reasons)


def test_downtrend_then_structure_weakening_transition():
    down = structure("DOWNTREND_STRUCTURE", "LH", "LL")
    assert classify_stage(row(close=100, ma5=105, ma20=110, foreign_5d=-100), down, evidence()).stage == "A_DOWNTREND"
    weak = classify_stage(row(close=100, ma5=105, ma20=110, foreign_5d=-100), down, evidence(), row(), "F_HIGH_LEVEL_CORRECTION")
    assert weak.stage == "G_STRUCTURE_WEAKENING"


def test_missing_core_inputs_are_unclassified():
    actual = classify_stage(row(ma20=float("nan")), None, [])
    assert actual.stage == "UNCLASSIFIED"
    assert actual.evidence_factors == []
