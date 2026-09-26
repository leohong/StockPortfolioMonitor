from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from src.models_v3 import CapitalFlowState


PARTICIPANTS = {"FOREIGN":"foreign_net", "INVESTMENT_TRUST":"investment_trust_net", "DEALER":"dealer_net"}


def calculate_capital_flow(data: pd.DataFrame, ruleset_version: str, *, persistence_ratio: float = .7) -> list[CapitalFlowState]:
    frame = data.sort_values("market_date").reset_index(drop=True).copy()
    frame["market_date"] = pd.to_datetime(frame.market_date).dt.date
    output = []
    for participant, column in PARTICIPANTS.items():
        series = frame[column]
        sums = {window: series.rolling(window, min_periods=window).sum() for window in (3,5,10,20)}
        positive = (series > 0).rolling(10, min_periods=10).sum()
        negative = (series < 0).rolling(10, min_periods=10).sum()
        valid = series.notna().rolling(10, min_periods=10).sum()
        persistence = positive / valid.replace(0, pd.NA)
        for index, row in frame.iterrows():
            flows = {1: series.iloc[index], **{window: values.iloc[index] for window,values in sums.items()}}
            missing = [] if not pd.isna(flows[10]) else ["10_valid_observations"]
            if missing:
                state = "INSUFFICIENT_DATA"
            else:
                prior_direction = None if pd.isna(flows[20]) else flows[20] - flows[10]
                if flows[3] > 0 and prior_direction is not None and prior_direction < 0:
                    state = "REVERSING_POSITIVE"
                elif flows[3] < 0 and prior_direction is not None and prior_direction > 0:
                    state = "REVERSING_NEGATIVE"
                elif flows[10] > 0 and persistence.iloc[index] >= persistence_ratio:
                    state = "PERSISTENT_BUYING"
                elif flows[10] < 0 and negative.iloc[index]/valid.iloc[index] >= persistence_ratio:
                    state = "PERSISTENT_SELLING"
                elif flows[5] > 0:
                    state = "BUYING"
                elif flows[5] < 0:
                    state = "SELLING"
                else:
                    state = "NEUTRAL"
            values = {f"net_flow_{window}d": None if pd.isna(value) else int(value) for window,value in flows.items()}
            metrics = {**values, "positive_days_10d":None if pd.isna(positive.iloc[index]) else int(positive.iloc[index]),
                       "negative_days_10d":None if pd.isna(negative.iloc[index]) else int(negative.iloc[index]),
                       "flow_persistence_10d":None if pd.isna(persistence.iloc[index]) else float(persistence.iloc[index])}
            observations = [{"metric":key,"value":value,"unit":"shares" if key.startswith("net_flow") else "ratio" if "persistence" in key else "days"} for key,value in metrics.items() if value is not None]
            output.append(CapitalFlowState(ticker=str(row.ticker), market_date=row.market_date,
                participant=participant, state=state, **metrics, observations=observations, missing_inputs=missing,
                source_dates=frame.market_date.iloc[max(0,index-19):index+1].tolist(), ruleset_version=ruleset_version,
                created_at=datetime.now(timezone.utc)))
    return sorted(output, key=lambda item:(item.market_date,item.participant))
