from __future__ import annotations

from datetime import datetime, timezone
import numpy as np
import pandas as pd

from src.models_v3 import VolatilityState


def calculate_volatility(data: pd.DataFrame, ruleset_version: str, *, compressed=.2, expanding=.7,
                         high=.9, shock_range=2.5) -> list[VolatilityState]:
    frame=data.sort_values("market_date").reset_index(drop=True).copy()
    frame["market_date"]=pd.to_datetime(frame.market_date).dt.date
    previous=frame.close.shift(1)
    frame["true_range"]=pd.concat([(frame.high-frame.low),(frame.high-previous).abs(),(frame.low-previous).abs()],axis=1).max(axis=1)
    frame["atr14"]=frame.true_range.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    frame["atr14_pct"]=frame.atr14/frame.close*100
    log_return=np.log(frame.close/frame.close.shift(1))
    frame["historical_volatility_20d"]=log_return.rolling(20,min_periods=20).std(ddof=1)*np.sqrt(252)*100
    frame["range_ratio"]=(frame.high-frame.low)/frame.atr14
    frame["gap_pct"]=(frame.open/previous-1)*100
    frame["volatility_percentile"]=frame.atr14_pct.rolling(252,min_periods=60).apply(lambda values: float((values <= values[-1]).sum()/len(values)),raw=True)
    output=[]
    for index,row in frame.iterrows():
        fields=("atr14","atr14_pct","historical_volatility_20d","range_ratio","gap_pct","volatility_percentile")
        values={name:None if pd.isna(row[name]) else float(row[name]) for name in fields}
        missing=[name for name in fields if values[name] is None]
        if missing: state="INSUFFICIENT_DATA"
        elif row.range_ratio >= shock_range or abs(row.gap_pct) >= row.atr14_pct*2: state="SHOCK"
        elif row.volatility_percentile >= high: state="HIGH"
        elif row.volatility_percentile >= expanding: state="EXPANDING"
        elif row.volatility_percentile <= compressed: state="COMPRESSED"
        else: state="NORMAL"
        observations=[{"metric":key,"value":value,"unit":"%" if key in {"atr14_pct","historical_volatility_20d","gap_pct"} else "TWD" if key=="atr14" else "ratio"} for key,value in values.items() if value is not None]
        output.append(VolatilityState(ticker=str(row.ticker),market_date=row.market_date,state=state,**values,
            observations=observations,missing_inputs=missing,source_dates=frame.market_date.iloc[max(0,index-251):index+1].tolist(),
            ruleset_version=ruleset_version,created_at=datetime.now(timezone.utc)))
    return output
