from datetime import date, timedelta

import pandas as pd

from src.analysis.trend.trend_quality import calculate_trend_quality


def series(step=.5, count=160):
    close = [100+step*i for i in range(count)]
    return pd.DataFrame({"ticker":["3702"]*count,
        "market_date":[date(2026,1,1)+timedelta(days=i) for i in range(count)], "close":close})


def test_trend_quality_uses_ma120_slopes_separation_and_persistence():
    item = calculate_trend_quality(series(), "m3", extended_distance_pct=20)[-1]
    assert item.state == "TREND_HEALTHY"
    assert item.ma5 > item.ma20 > item.ma60 > item.ma120
    assert item.ma20_slope_5d_pct > 0 and item.ma60_slope_5d_pct > 0
    assert item.persistence_20d == 1


def test_trend_history_is_insufficient_before_ma120_and_decline_breaks():
    assert calculate_trend_quality(series(count=100), "m3")[-1].state == "INSUFFICIENT_DATA"
    assert calculate_trend_quality(series(step=-.3), "m3")[-1].state == "TREND_BROKEN"
