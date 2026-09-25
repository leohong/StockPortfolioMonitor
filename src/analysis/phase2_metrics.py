import numpy as np
import pandas as pd


def calculate_phase2(institutional: pd.DataFrame, margin: pd.DataFrame):
    inst = institutional.copy()
    for participant in ("foreign", "investment_trust", "dealer"):
        for window in (3, 5, 10, 20):
            inst[f"{participant}_{window}d"] = inst[f"{participant}_net"].rolling(window, min_periods=window).sum()
    mar = margin.copy()
    mar["margin_change_1d"] = mar.margin_balance.diff(1)
    for window in (5, 10, 20):
        mar[f"margin_change_{window}d"] = mar.margin_balance.diff(window)
    denominator = mar.margin_balance.shift(20).replace(0, np.nan)
    mar["margin_change_pct_20d"] = mar.margin_change_20d / denominator * 100
    return inst, mar
