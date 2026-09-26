from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from src.indicators.core import rsi_wilder
from src.models_v3 import MomentumState


def _cross(previous, current):
    if pd.isna(previous) or pd.isna(current):
        return None
    for threshold in (30, 50, 70, 80):
        if previous < threshold <= current:
            return f"{threshold}_UP"
        if previous > threshold >= current:
            return f"{threshold}_DOWN"
    return None


def _divergence(day, pivots, rsi_by_date):
    confirmed = [pivot for pivot in pivots if pivot.confirmation_date <= day]
    for kind, label, direction in (("LOW", "BULLISH", 1), ("HIGH", "BEARISH", -1)):
        comparable = [pivot for pivot in confirmed if pivot.pivot_kind == kind]
        if len(comparable) < 2:
            continue
        previous, current = comparable[-2:]
        prior_rsi, current_rsi = rsi_by_date.get(previous.pivot_date), rsi_by_date.get(current.pivot_date)
        price_condition = current.price < previous.price if kind == "LOW" else current.price > previous.price
        rsi_condition = current_rsi > prior_rsi if direction == 1 and None not in (prior_rsi,current_rsi) else current_rsi < prior_rsi if None not in (prior_rsi,current_rsi) else False
        if price_condition and rsi_condition:
            return label, current.pivot_date, current.confirmation_date
    return None, None, None


def calculate_momentum(data: pd.DataFrame, pivots, ruleset_version: str) -> list[MomentumState]:
    frame = data.sort_values("market_date").reset_index(drop=True).copy()
    frame["market_date"] = pd.to_datetime(frame.market_date).dt.date
    frame["rsi14"] = rsi_wilder(frame.close)
    frame["rsi_change_5d"] = frame.rsi14.diff(5)
    frame["roc20"] = frame.close.pct_change(20, fill_method=None) * 100
    rsi_by_date = {row.market_date: None if pd.isna(row.rsi14) else float(row.rsi14) for row in frame.itertuples()}
    output = []
    for index, row in enumerate(frame.itertuples()):
        previous_rsi = frame.iloc[index-1].rsi14 if index else float("nan")
        cross = _cross(previous_rsi, row.rsi14)
        divergence, pivot_date, confirmation_date = _divergence(row.market_date, pivots, rsi_by_date)
        if any(pd.isna(value) for value in (row.rsi14, row.rsi_change_5d, row.roc20)):
            state = "INSUFFICIENT_DATA"
        elif row.rsi14 >= 55 and row.rsi_change_5d > 3 and row.roc20 > 0:
            state = "ACCELERATING"
        elif row.rsi14 >= 50 and row.rsi_change_5d < -2:
            state = "COOLING"
        elif row.rsi14 >= 50 and row.roc20 >= 0:
            state = "POSITIVE"
        elif 45 <= row.rsi14 <= 55 and abs(row.roc20) <= 5:
            state = "RESET"
        elif row.rsi14 < 45 and row.roc20 < 0:
            state = "NEGATIVE"
        elif row.rsi14 < 50 and row.rsi_change_5d < 0:
            state = "WEAKENING"
        else:
            state = "NEUTRAL"
        values = {name: None if pd.isna(getattr(row,name)) else float(getattr(row,name)) for name in ("rsi14","rsi_change_5d","roc20")}
        observations = [{"metric":name,"value":value} for name,value in values.items() if value is not None]
        if cross: observations.append({"metric":"rsi_cross","value":cross})
        if divergence: observations.append({"metric":"confirmed_rsi_divergence","value":divergence,"pivot_date":str(pivot_date),"confirmation_date":str(confirmation_date)})
        dates = [row.market_date] + ([confirmation_date] if confirmation_date else [])
        output.append(MomentumState(ticker=str(row.ticker), market_date=row.market_date, state=state,
            **values, rsi_cross=cross, divergence=divergence, divergence_pivot_date=pivot_date,
            divergence_confirmation_date=confirmation_date, observations=observations,
            source_dates=sorted(set(dates)), ruleset_version=ruleset_version, created_at=datetime.now(timezone.utc)))
    return output
