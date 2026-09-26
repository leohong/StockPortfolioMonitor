from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from src.models_v3 import PositioningState


def calculate_positioning(stock: pd.DataFrame, margin: pd.DataFrame, ruleset_version: str, *,
                          expansion_pct: float = 10, crowded_pct: float = 20,
                          deleveraging_pct: float = -5) -> list[PositioningState]:
    prices = stock[["ticker","market_date","close","turnover"]].copy()
    frame = margin.merge(prices, on=["ticker","market_date"], how="left").sort_values("market_date").reset_index(drop=True)
    frame["market_date"] = pd.to_datetime(frame.market_date).dt.date
    for window in (5,10,20):
        frame[f"margin_change_{window}d"] = frame.margin_balance.diff(window)
        frame[f"margin_change_pct_{window}d"] = frame.margin_balance.pct_change(window, fill_method=None)*100
        frame[f"short_change_{window}d"] = frame.short_balance.diff(window)
    frame["price_return_pct_20d"] = frame.close.pct_change(20, fill_method=None)*100
    frame["leverage_divergence_20d"] = frame.margin_change_pct_20d-frame.price_return_pct_20d
    frame["turnover_ratio_20"] = frame.turnover/frame.turnover.rolling(20,min_periods=20).mean().replace(0,pd.NA)
    output=[]
    for index,row in frame.iterrows():
        required=(row.margin_change_pct_20d,row.price_return_pct_20d,row.leverage_divergence_20d,row.turnover_ratio_20)
        missing=[name for name,value in zip(("margin_change_pct_20d","price_return_pct_20d","leverage_divergence_20d","turnover_ratio_20"),required) if pd.isna(value)]
        if missing: state="INSUFFICIENT_DATA"
        elif row.price_return_pct_20d < 0 and row.margin_change_pct_20d >= expansion_pct: state="STRESS"
        elif row.margin_change_pct_20d >= crowded_pct and row.turnover_ratio_20 >= 1.2: state="CROWDED"
        elif row.margin_change_pct_20d >= expansion_pct: state="LEVERAGE_EXPANDING"
        elif row.margin_change_pct_20d <= deleveraging_pct: state="DELEVERAGING"
        elif row.price_return_pct_20d > 0 and 0 <= row.margin_change_pct_20d < expansion_pct: state="HEALTHY"
        else: state="NORMAL"
        integer_fields=("margin_balance","margin_change_5d","margin_change_10d","margin_change_20d","short_balance","short_change_5d","short_change_10d","short_change_20d")
        float_fields=("margin_change_pct_5d","margin_change_pct_10d","margin_change_pct_20d","price_return_pct_20d","leverage_divergence_20d","turnover_ratio_20")
        values={name:None if pd.isna(getattr(row,name)) else int(getattr(row,name)) for name in integer_fields}
        values.update({name:None if pd.isna(getattr(row,name)) else float(getattr(row,name)) for name in float_fields})
        observations=[{"metric":key,"value":value,"unit":"trading_units" if key in integer_fields else "%" if "pct" in key or "return" in key or "divergence" in key else "ratio"} for key,value in values.items() if value is not None]
        output.append(PositioningState(ticker=str(row.ticker),market_date=row.market_date,state=state,**values,
            observations=observations,missing_inputs=missing,source_dates=frame.market_date.iloc[max(0,index-20):index+1].tolist(),
            ruleset_version=ruleset_version,created_at=datetime.now(timezone.utc)))
    return output
