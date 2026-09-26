from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from src.models_v3 import TrendQuality


def calculate_trend_quality(data: pd.DataFrame, ruleset_version: str, *, extended_distance_pct: float = 8,
                            persistence_min: float = .7) -> list[TrendQuality]:
    frame = data.sort_values("market_date").reset_index(drop=True).copy()
    frame["market_date"] = pd.to_datetime(frame.market_date).dt.date
    for window in (5, 20, 60, 120):
        frame[f"ma{window}"] = frame.close.rolling(window, min_periods=window).mean()
    for window in (20, 60, 120):
        frame[f"ma{window}_slope_5d_pct"] = frame[f"ma{window}"].pct_change(5, fill_method=None) * 100
    frame["distance_ma20_pct"] = (frame.close/frame.ma20-1)*100
    frame["distance_ma60_pct"] = (frame.close/frame.ma60-1)*100
    frame["ma20_ma60_separation_pct"] = (frame.ma20/frame.ma60-1)*100
    frame["persistence_20d"] = (frame.close > frame.ma20).rolling(20, min_periods=20).mean()
    output = []
    for row in frame.itertuples():
        required = (row.ma20, row.ma60, row.ma120, row.ma20_slope_5d_pct, row.ma60_slope_5d_pct,
                    row.ma120_slope_5d_pct, row.persistence_20d)
        if any(pd.isna(value) for value in required):
            state = "INSUFFICIENT_DATA"
        elif row.close < row.ma60 and row.ma20_slope_5d_pct < 0 and row.ma60_slope_5d_pct < 0:
            state = "TREND_BROKEN"
        elif row.close > row.ma20 > row.ma60 > row.ma120 and row.persistence_20d >= persistence_min:
            state = "TREND_EXTENDED" if row.distance_ma20_pct >= extended_distance_pct else "TREND_HEALTHY"
        elif row.close > row.ma20 and row.ma20_slope_5d_pct > 0 and row.persistence_20d >= .5:
            state = "TREND_EMERGING"
        elif row.close >= row.ma60 and row.ma20_slope_5d_pct <= 0:
            state = "TREND_DECELERATING"
        elif abs(row.distance_ma20_pct) <= 3 and abs(row.ma20_slope_5d_pct) <= 1:
            state = "RANGE"
        else:
            state = "TREND_DECELERATING"
        fields = ("ma5","ma20","ma60","ma120","ma20_slope_5d_pct","ma60_slope_5d_pct",
                  "ma120_slope_5d_pct","distance_ma20_pct","distance_ma60_pct",
                  "ma20_ma60_separation_pct","persistence_20d")
        values = {name: None if pd.isna(getattr(row,name)) else float(getattr(row,name)) for name in fields}
        observations = [{"metric":name,"value":value} for name,value in values.items() if value is not None]
        output.append(TrendQuality(ticker=str(row.ticker), market_date=row.market_date, state=state,
            **values, observations=observations, source_dates=[row.market_date], ruleset_version=ruleset_version,
            created_at=datetime.now(timezone.utc)))
    return output
