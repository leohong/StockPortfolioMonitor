from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from src.models_v3 import ParticipationState


def calculate_participation(data: pd.DataFrame, ruleset_version: str, *, confirm_ratio: float = 1.2,
                            strong_ratio: float = 1.5, abnormal_ratio: float = 2.5) -> list[ParticipationState]:
    frame = data.sort_values("market_date").reset_index(drop=True).copy()
    frame["market_date"] = pd.to_datetime(frame.market_date).dt.date
    frame["volume_ma5"] = frame.volume.rolling(5, min_periods=5).mean()
    frame["volume_ma20"] = frame.volume.rolling(20, min_periods=20).mean()
    frame["volume_ratio_20"] = frame.volume / frame.volume_ma20.replace(0, pd.NA)
    daily_range = frame.high - frame.low
    frame["close_location_value"] = ((frame.close-frame.low)/daily_range).where(daily_range != 0, .5)
    frame["prior_high_20"] = frame.high.rolling(20, min_periods=20).max().shift(1)
    frame["prior_low_20"] = frame.low.rolling(20, min_periods=20).min().shift(1)
    output = []
    for index, row in frame.iterrows():
        needed = [row.volume_ma20, row.volume_ratio_20, row.close_location_value, row.prior_high_20, row.prior_low_20]
        missing = [name for name, value in zip(("volume_ma20","volume_ratio_20","close_location_value","prior_high_20","prior_low_20"), needed) if pd.isna(value)]
        breakout = None if missing else bool(row.close > row.prior_high_20)
        breakdown = None if missing else bool(row.close < row.prior_low_20)
        if missing:
            state = "INSUFFICIENT_DATA"
        else:
            aligned = (breakout and row.close_location_value >= .75) or (breakdown and row.close_location_value <= .25)
            opposed = (breakout and row.close_location_value < .5) or (breakdown and row.close_location_value > .5)
            event = breakout or breakdown
            if event and aligned and row.volume_ratio_20 >= strong_ratio:
                state = "STRONG_CONFIRMATION"
            elif event and aligned and row.volume_ratio_20 >= confirm_ratio:
                state = "CONFIRMING"
            elif event and (opposed or row.volume_ratio_20 < .8):
                state = "CONTRADICTORY"
            elif event:
                state = "WEAK_CONFIRMATION"
            elif row.volume_ratio_20 >= abnormal_ratio:
                state = "ABNORMAL"
            else:
                state = "NORMAL"
        numeric = {"volume": row.volume, "volume_ma5": row.volume_ma5, "volume_ma20": row.volume_ma20,
                   "volume_ratio_20": row.volume_ratio_20, "turnover": row.turnover,
                   "close_location_value": row.close_location_value}
        values = {key: None if pd.isna(value) else (int(value) if key in {"volume","turnover"} else float(value)) for key,value in numeric.items()}
        observations = [{"metric": key, "value": value, "unit": "shares" if key.startswith("volume") else "TWD" if key == "turnover" else "ratio"} for key,value in values.items() if value is not None]
        observations += [{"metric":"breakout","value":breakout},{"metric":"breakdown","value":breakdown}]
        start = max(0, index-20)
        output.append(ParticipationState(ticker=str(row.ticker), market_date=row.market_date, state=state,
            **values, breakout=breakout, breakdown=breakdown, observations=observations, missing_inputs=missing,
            source_dates=frame.market_date.iloc[start:index+1].tolist(), ruleset_version=ruleset_version,
            created_at=datetime.now(timezone.utc)))
    return output
