from datetime import date, datetime, timezone

from src.analysis.snapshot import changed_tickers, detect_changes
from src.models import AnalysisSnapshot


def snapshot(day, **changes):
    values = dict(ticker="3702", market_date=day, close=100, market_stage="D_UPTREND", structure_state="UPTREND_STRUCTURE",
        latest_pivot_type=None, rsi14=49, ma5=99, ma20=100, ma60=95, volume_ratio_20=1.0,
        foreign_5d=-100, foreign_20d=-200, trust_5d=-20, trust_20d=-50, dealer_5d=0,
        margin_balance=1000, margin_change_5d=10, margin_change_20d=100, margin_change_pct_20d=10,
        support_1=95, support_2=90, resistance_1=105, resistance_2=110,
        bullish_evidence_count=3, bearish_evidence_count=1, warning_count=0,
        data_quality_status="PASS", created_at=datetime(2026,1,1,tzinfo=timezone.utc))
    values.update(changes)
    return AnalysisSnapshot(**values)


def test_snapshot_change_detection_priorities():
    previous = snapshot(date(2026,1,1), close=99)
    current = snapshot(date(2026,1,2), close=106, market_stage="E_OVERHEATED", rsi14=72,
        ma5=102, volume_ratio_20=1.7, foreign_5d=200, trust_5d=30,
        margin_change_pct_20d=25, latest_pivot_type="HH")
    events = {event.change_type:event for event in detect_changes(previous,current)}
    expected = {"MARKET_STAGE_CHANGED","RSI_50_UP","RSI_70_UP","MA5_MA20_CROSS_UP","PRICE_MA20_CROSS_UP",
                "NEW_HH","RESISTANCE_BROKEN","FOREIGN_5D_SIGN_CHANGED","TRUST_5D_SIGN_CHANGED",
                "MARGIN_ACCELERATION_UP","VOLUME_RATIO_1_5_UP"}
    assert expected <= events.keys()
    assert events["MARKET_STAGE_CHANGED"].severity == "IMPORTANT"
    assert events["RESISTANCE_BROKEN"].severity == "IMPORTANT"


def test_support_break_and_reclaim_events():
    broken = detect_changes(snapshot(date(2026,1,1),close=100,support_1=95), snapshot(date(2026,1,2),close=94,support_1=90))
    assert next(x for x in broken if x.change_type=="SUPPORT_BROKEN").severity == "CRITICAL"
    reclaimed = detect_changes(snapshot(date(2026,1,2),close=94,support_1=95), snapshot(date(2026,1,3),close=96))
    assert any(x.change_type=="SUPPORT_RECLAIMED" for x in reclaimed)


def test_changed_holdings_filter_excludes_info_only():
    prior = snapshot(date(2026,1,1), margin_change_pct_20d=25)
    current = snapshot(date(2026,1,2), margin_change_pct_20d=15)
    events = detect_changes(prior,current)
    assert [x.severity for x in events if x.change_type=="MARGIN_ACCELERATION_DOWN"] == ["INFO"]
    assert changed_tickers(events,date(2026,1,2)) == []
    assert changed_tickers(events,date(2026,1,2),meaningful_only=False) == ["3702"]


def test_same_snapshots_produce_same_events():
    previous,current=snapshot(date(2026,1,1)),snapshot(date(2026,1,2),rsi14=51)
    assert [x.model_dump() for x in detect_changes(previous,current)] == [x.model_dump() for x in detect_changes(previous,current)]
