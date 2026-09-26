from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from src.models_v3 import RelativeStrengthState


def calculate_relative_strength(stock: pd.DataFrame, benchmark: pd.DataFrame, ruleset_version: str, *,
                                leading_20d_pct: float = 3, leading_60d_pct: float = 5) -> list[RelativeStrengthState]:
    left = stock.sort_values("market_date").copy()
    right = benchmark.sort_values("market_date")[["market_date","close"]].rename(columns={"close":"benchmark_close"})
    left["market_date"] = pd.to_datetime(left.market_date).dt.date
    right["market_date"] = pd.to_datetime(right.market_date).dt.date
    frame = left.merge(right, on="market_date", how="left", validate="one_to_one")
    frame["rs_line"] = frame.close/frame.benchmark_close
    first = frame.rs_line.dropna().iloc[0] if frame.rs_line.notna().any() else float("nan")
    frame["rs_line_indexed"] = frame.rs_line/first*100
    for window in (20,60,120):
        stock_return = frame.close.pct_change(window, fill_method=None)*100
        benchmark_return = frame.benchmark_close.pct_change(window, fill_method=None)*100
        frame[f"rs_market_{window}d"] = stock_return-benchmark_return
    frame["rs_line_change_20d"] = frame.rs_line.pct_change(20, fill_method=None)*100
    notes = frame.source_note.fillna("") if "source_note" in frame else pd.Series("", index=frame.index)
    frame["corporate_action_warning"] = notes.str.contains("X", regex=False).rolling(120, min_periods=1).max().astype(bool)
    output = []
    for row in frame.itertuples():
        required = (row.benchmark_close, row.rs_market_20d, row.rs_market_60d, row.rs_market_120d, row.rs_line_change_20d)
        missing = []
        if any(pd.isna(value) for value in required):
            state = "INSUFFICIENT_DATA"
            if pd.isna(row.benchmark_close): missing.append("benchmark_date_alignment")
            else: missing.append("relative_strength_history")
        elif row.rs_market_20d >= leading_20d_pct and row.rs_market_60d >= leading_60d_pct and row.rs_line_change_20d > 0:
            state = "LEADING"
        elif row.rs_market_20d > 0 and row.rs_line_change_20d > 0:
            state = "IMPROVING"
        elif row.rs_market_20d <= -leading_20d_pct and row.rs_market_60d <= -leading_60d_pct and row.rs_line_change_20d < 0:
            state = "LAGGING"
        elif row.rs_market_20d < 0 and row.rs_line_change_20d < 0:
            state = "WEAKENING"
        else:
            state = "NEUTRAL"
        missing.append("sector_benchmark")
        values = {name: None if pd.isna(getattr(row,name)) else float(getattr(row,name)) for name in
                  ("rs_line","rs_line_indexed","rs_market_20d","rs_market_60d","rs_market_120d","rs_line_change_20d")}
        benchmark_date = None if pd.isna(row.benchmark_close) else row.market_date
        source_dates = [row.market_date] if benchmark_date else []
        output.append(RelativeStrengthState(ticker=str(row.ticker), market_date=row.market_date,
            benchmark_date=benchmark_date, **values, state=state, missing_inputs=sorted(set(missing)),
            corporate_action_warning=bool(row.corporate_action_warning), source_dates=source_dates,
            ruleset_version=ruleset_version, created_at=datetime.now(timezone.utc)))
    return output
