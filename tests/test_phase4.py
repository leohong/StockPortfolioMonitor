from datetime import date
from types import SimpleNamespace

from src.analysis.evidence import FACTORS, build_evidence
from src.models import PriceLevel, StructureSnapshot


def row(**updates):
    values = dict(ticker="3702", market_date=date(2026,9,24), rsi14=74.0, ma5=120.0, ma20=115.0, ma60=110.0,
        volume_ratio_20=1.1, foreign_5d=1000, investment_trust_5d=-100, dealer_5d=50,
        margin_balance=13472, margin_change_pct_20d=34.0)
    values.update(updates)
    return SimpleNamespace(**values)


def context():
    structure = StructureSnapshot(ticker="3702", market_date=date(2026,9,24), state="UPTREND_STRUCTURE",
        high_label="HH", high_pivot_date=date(2026,9,18), high_price=122,
        low_label="HL", low_pivot_date=date(2026,9,10), low_price=110)
    levels = [PriceLevel(ticker="3702", market_date=date(2026,9,24), level_type="SUPPORT", rank=1, price=114,
        derivation="壓力突破後轉為支撐", evidence_date=date(2026,9,1)),
        PriceLevel(ticker="3702", market_date=date(2026,9,24), level_type="RESISTANCE", rank=1, price=122,
        derivation="確認波段高點", evidence_date=date(2026,9,18), source_confirmation_date=date(2026,9,23))]
    return structure, levels


def test_seven_structured_evidence_objects_are_traceable_without_score():
    evidence = build_evidence(row(), *context())
    assert tuple(item.factor for item in evidence) == FACTORS
    assert len(evidence) == 7
    assert all(item.headline and item.reasoning and item.updated_at and item.source_dates for item in evidence)
    assert evidence[0].observations[0] == {"metric":"latest_high", "label":"HH", "value":122.0, "unit":"TWD", "date":"2026-09-18"}
    assert evidence[1].status == "WARNING"
    assert evidence[2].status == "BULLISH"
    assert not any(hasattr(item, "score") for item in evidence)


def test_missing_data_is_explicitly_insufficient():
    missing = row(rsi14=float("nan"), ma5=float("nan"), ma20=float("nan"), ma60=float("nan"),
                  volume_ratio_20=float("nan"), foreign_5d=float("nan"), margin_change_pct_20d=float("nan"))
    evidence = build_evidence(missing, None, [])
    assert len(evidence) == 7
    assert all(item.status == "INSUFFICIENT_DATA" for item in evidence)
    assert all(item.current_value == "—" for item in evidence)


def test_volume_never_claims_direction_and_margin_is_warning():
    evidence = {item.factor:item for item in build_evidence(row(volume_ratio_20=2.5), *context())}
    assert evidence["volume"].status == "WARNING"
    assert "不代表方向" in evidence["volume"].reasoning
    assert evidence["margin"].status == "WARNING"
