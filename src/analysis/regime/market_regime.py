from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.indicators.core import rsi_wilder
from src.models_v3 import RegimeEvidence


def _observation(metric, value, relation=None):
    item = {"metric": metric, "value": None if pd.isna(value) else float(value)}
    if relation:
        item["relation"] = relation
    return item


def calculate_market_regimes(data: pd.DataFrame, ruleset_version: str, breadth: pd.DataFrame | None = None,
                             context_type: str = "MARKET", context_id: str = "TAIEX") -> list[RegimeEvidence]:
    frame = data.sort_values("market_date").reset_index(drop=True).copy()
    frame["market_date"] = pd.to_datetime(frame.market_date).dt.date
    for window in (20, 60, 120):
        frame[f"ma{window}"] = frame.close.rolling(window, min_periods=window).mean()
    frame["ma20_slope_5d_pct"] = frame.ma20.pct_change(5, fill_method=None) * 100
    frame["ma60_slope_5d_pct"] = frame.ma60.pct_change(5, fill_method=None) * 100
    frame["rsi14"] = rsi_wilder(frame.close)
    previous_close = frame.close.shift(1)
    true_range = pd.concat([(frame.high-frame.low).abs(), (frame.high-previous_close).abs(),
                            (frame.low-previous_close).abs()], axis=1).max(axis=1)
    frame["atr14_pct"] = true_range.rolling(14, min_periods=14).mean() / frame.close * 100
    breadth_dates = set() if breadth is None or breadth.empty else set(pd.to_datetime(breadth.market_date).dt.date)
    output = []
    for row in frame.itertuples():
        missing = []
        required = (row.ma20, row.ma60, row.ma20_slope_5d_pct, row.ma60_slope_5d_pct, row.rsi14, row.atr14_pct)
        if any(pd.isna(value) for value in required):
            missing.extend(name for name, value in zip(("ma20","ma60","ma20_slope_5d_pct","ma60_slope_5d_pct","rsi14","atr14_pct"), required) if pd.isna(value))
            regime, confidence, evidence_for, evidence_against = "INSUFFICIENT_DATA", "INSUFFICIENT", [], []
        else:
            bullish = [
                _observation("close_vs_ma20", row.close-row.ma20, "above") if row.close > row.ma20 else None,
                _observation("ma20_vs_ma60", row.ma20-row.ma60, "above") if row.ma20 > row.ma60 else None,
                _observation("ma20_slope_5d_pct", row.ma20_slope_5d_pct, "positive") if row.ma20_slope_5d_pct > 0 else None,
                _observation("ma60_slope_5d_pct", row.ma60_slope_5d_pct, "positive") if row.ma60_slope_5d_pct > 0 else None,
                _observation("rsi14", row.rsi14, "above_50") if row.rsi14 > 50 else None,
            ]
            bearish = [
                _observation("close_vs_ma20", row.close-row.ma20, "below") if row.close < row.ma20 else None,
                _observation("ma20_vs_ma60", row.ma20-row.ma60, "below") if row.ma20 < row.ma60 else None,
                _observation("ma20_slope_5d_pct", row.ma20_slope_5d_pct, "negative") if row.ma20_slope_5d_pct < 0 else None,
                _observation("ma60_slope_5d_pct", row.ma60_slope_5d_pct, "negative") if row.ma60_slope_5d_pct < 0 else None,
                _observation("rsi14", row.rsi14, "below_50") if row.rsi14 < 50 else None,
            ]
            bullish, bearish = [x for x in bullish if x], [x for x in bearish if x]
            distance_ma20 = (row.close / row.ma20 - 1) * 100
            if len(bullish) >= 4:
                regime = "RISK_ON_EXTENDED" if row.rsi14 >= 70 or distance_ma20 >= 8 else "RISK_ON_TREND"
                evidence_for, evidence_against = bullish, bearish
            elif len(bearish) >= 4:
                regime, evidence_for, evidence_against = "RISK_OFF", bearish, bullish
            elif abs(distance_ma20) <= 3 and abs(row.ma20_slope_5d_pct) <= 1:
                regime, evidence_for, evidence_against = "RANGE_ROTATION", [
                    _observation("distance_ma20_pct", distance_ma20, "near"),
                    _observation("ma20_slope_5d_pct", row.ma20_slope_5d_pct, "flat")], bullish + bearish
            else:
                regime, evidence_for, evidence_against = "TRANSITION", bullish + bearish, []
            confidence = "CONFIRMED" if len(evidence_for) >= 4 and not evidence_against else "MIXED" if evidence_against else "TENTATIVE"
        if row.market_date not in breadth_dates:
            missing.append("market_breadth")
        output.append(RegimeEvidence(context_type=context_type, context_id=context_id, market_date=row.market_date,
            regime=regime, confidence_class=confidence, evidence_for=evidence_for, evidence_against=evidence_against,
            missing_inputs=sorted(set(missing)), source_dates=[row.market_date], ruleset_version=ruleset_version,
            created_at=datetime.now(timezone.utc)))
    return output


def regime_as_of(data: pd.DataFrame, as_of, ruleset_version: str, **kwargs) -> RegimeEvidence | None:
    history = data[pd.to_datetime(data.market_date).dt.date <= as_of]
    regimes = calculate_market_regimes(history, ruleset_version, **kwargs)
    return regimes[-1] if regimes else None
