from __future__ import annotations

import pandas as pd

from src.models import PriceLevel, PricePivot, StructureSnapshot


def detect_pivots(data: pd.DataFrame, left: int = 3, right: int = 3, as_of=None) -> list[PricePivot]:
    frame = data.sort_values("market_date").reset_index(drop=True).copy()
    frame["market_date"] = pd.to_datetime(frame.market_date).dt.date
    if as_of is not None:
        frame = frame[frame.market_date <= as_of].reset_index(drop=True)
    result, previous = [], {"HIGH": None, "LOW": None}
    for i in range(left, len(frame) - right):
        row = frame.iloc[i]
        windows = {
            "HIGH": ("high", row.high > frame.high.iloc[i-left:i].max() and row.high >= frame.high.iloc[i+1:i+right+1].max()),
            "LOW": ("low", row.low < frame.low.iloc[i-left:i].min() and row.low <= frame.low.iloc[i+1:i+right+1].min()),
        }
        for kind, (column, matched) in windows.items():
            if not matched:
                continue
            prior = previous[kind]
            price = float(row[column])
            label = None
            if prior is not None and price != prior.price:
                label = ("HH" if price > prior.price else "LH") if kind == "HIGH" else ("HL" if price > prior.price else "LL")
            pivot = PricePivot(ticker=str(row.ticker), pivot_date=row.market_date,
                confirmation_date=frame.iloc[i + right].market_date, pivot_kind=kind, price=price,
                structure_label=label, comparison_date=prior.pivot_date if prior else None,
                comparison_price=prior.price if prior else None)
            result.append(pivot)
            previous[kind] = pivot
    return sorted(result, key=lambda p: (p.confirmation_date, p.pivot_date, p.pivot_kind))


def structure_snapshot(ticker: str, market_date, pivots: list[PricePivot]) -> StructureSnapshot:
    confirmed = [p for p in pivots if p.confirmation_date <= market_date and p.structure_label]
    high = next((p for p in reversed(confirmed) if p.pivot_kind == "HIGH"), None)
    low = next((p for p in reversed(confirmed) if p.pivot_kind == "LOW"), None)
    pair = (high.structure_label if high else None, low.structure_label if low else None)
    states = {("HH", "HL"): "UPTREND_STRUCTURE", ("LH", "LL"): "DOWNTREND_STRUCTURE",
              ("LH", "HL"): "POSSIBLE_BASE", ("HH", "LL"): "POSSIBLE_TOP"}
    state = states.get(pair, "UNCONFIRMED" if None in pair else "RANGE")
    return StructureSnapshot(ticker=ticker, market_date=market_date, state=state,
        high_label=high.structure_label if high else None, high_pivot_date=high.pivot_date if high else None,
        high_price=high.price if high else None, low_label=low.structure_label if low else None,
        low_pivot_date=low.pivot_date if low else None, low_price=low.price if low else None)


def derive_levels(data: pd.DataFrame, pivots: list[PricePivot], as_of, tolerance_pct: float = 2.0) -> list[PriceLevel]:
    history = data[pd.to_datetime(data.market_date).dt.date <= as_of].sort_values("market_date")
    if history.empty:
        return []
    last, ticker = history.iloc[-1], str(history.iloc[-1].ticker)
    close, tolerance = float(last.close), tolerance_pct / 100
    confirmed = [p for p in pivots if p.confirmation_date <= as_of]
    candidates = []
    for pivot in confirmed:
        if pivot.pivot_kind == "LOW":
            kind, derivation = ("SUPPORT", "確認波段低點") if pivot.price <= close else ("RESISTANCE", "支撐跌破後轉為壓力")
        else:
            kind, derivation = ("RESISTANCE", "確認波段高點") if pivot.price >= close else ("SUPPORT", "壓力突破後轉為支撐")
        candidates.append((kind, pivot.price, derivation, pivot.pivot_date, pivot.confirmation_date))
    for window in (20, 60):
        column = f"ma{window}"
        if column in history and pd.notna(last[column]):
            price = float(last[column]); kind = "SUPPORT" if price <= close else "RESISTANCE"
            candidates.append((kind, price, f"{window} 日移動平均", as_of, None))
    if len(history) >= 10:
        recent = history.tail(10)
        if (recent.high.max() - recent.low.min()) / close <= .06:
            price = float(recent.close.mean()); kind = "SUPPORT" if price <= close else "RESISTANCE"
            candidates.append((kind, price, "近 10 日盤整密集區", recent.iloc[0].market_date, None))
    if "volume_ratio_20" in history:
        for row in history.tail(60).itertuples():
            if pd.notna(row.volume_ratio_20) and row.volume_ratio_20 >= 1.8:
                price = float(row.close); kind = "SUPPORT" if price <= close else "RESISTANCE"
                candidates.append((kind, price, "近 60 日高成交量價格區", row.market_date, None))
    output = []
    for kind in ("SUPPORT", "RESISTANCE"):
        ordered = sorted((c for c in candidates if c[0] == kind), key=lambda c: abs(c[1] - close))
        chosen = []
        for candidate in ordered:
            if all(abs(candidate[1] - old[1]) / max(candidate[1], old[1]) > tolerance for old in chosen):
                chosen.append(candidate)
            if len(chosen) == 2:
                break
        for rank, item in enumerate(chosen, 1):
            output.append(PriceLevel(ticker=ticker, market_date=as_of, level_type=kind, rank=rank,
                price=item[1], derivation=item[2], evidence_date=item[3], source_confirmation_date=item[4]))
    return output
