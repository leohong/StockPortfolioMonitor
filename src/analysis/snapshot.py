from __future__ import annotations

import math
from datetime import timezone

from src.models import AnalysisSnapshot, ChangeEvent


def _value(row, name):
    value = getattr(row, name, None)
    return None if value is None or (isinstance(value, float) and math.isnan(value)) else value


def build_snapshot(row, stage, structure, pivots, levels, evidence, quality_status):
    day = row.market_date.date() if hasattr(row.market_date, "date") else row.market_date
    confirmed = [p for p in pivots if p.confirmation_date == day and p.structure_label]
    latest_pivot = confirmed[-1].structure_label if confirmed else None
    price_levels = {(item.level_type, item.rank): item.price for item in levels}
    retrieved = row.retrieved_at
    if retrieved.tzinfo is None:
        retrieved = retrieved.replace(tzinfo=timezone.utc)
    return AnalysisSnapshot(ticker=str(row.ticker), market_date=day, close=float(row.close),
        market_stage=stage.stage, structure_state=structure.state if structure else "UNCONFIRMED",
        latest_pivot_type=latest_pivot, rsi14=_value(row,"rsi14"), ma5=_value(row,"ma5"),
        ma20=_value(row,"ma20"), ma60=_value(row,"ma60"), volume_ratio_20=_value(row,"volume_ratio_20"),
        foreign_5d=_value(row,"foreign_5d"), foreign_20d=_value(row,"foreign_20d"),
        trust_5d=_value(row,"investment_trust_5d"), trust_20d=_value(row,"investment_trust_20d"),
        dealer_5d=_value(row,"dealer_5d"), margin_balance=_value(row,"margin_balance"),
        margin_change_5d=_value(row,"margin_change_5d"), margin_change_20d=_value(row,"margin_change_20d"),
        margin_change_pct_20d=_value(row,"margin_change_pct_20d"),
        support_1=price_levels.get(("SUPPORT",1)), support_2=price_levels.get(("SUPPORT",2)),
        resistance_1=price_levels.get(("RESISTANCE",1)), resistance_2=price_levels.get(("RESISTANCE",2)),
        bullish_evidence_count=sum(x.status == "BULLISH" for x in evidence),
        bearish_evidence_count=sum(x.status == "BEARISH" for x in evidence),
        warning_count=sum(x.status == "WARNING" for x in evidence), data_quality_status=quality_status,
        created_at=retrieved)


def _crossed(previous, current, threshold):
    if previous is None or current is None: return None
    if previous < threshold <= current: return "UP"
    if previous > threshold >= current: return "DOWN"
    return None


def detect_changes(previous: AnalysisSnapshot, current: AnalysisSnapshot) -> list[ChangeEvent]:
    events = []
    def add(kind, severity, old, new, explanation):
        events.append(ChangeEvent(ticker=current.ticker, market_date=current.market_date, change_type=kind,
            severity=severity, previous_value=str(old), current_value=str(new), explanation=explanation))
    if previous.market_stage != current.market_stage:
        add("MARKET_STAGE_CHANGED", "IMPORTANT", previous.market_stage, current.market_stage, "市場階段依固定規則發生變化。")
    for threshold in (30,50,70,80):
        direction = _crossed(previous.rsi14, current.rsi14, threshold)
        if direction: add(f"RSI_{threshold}_{direction}", "IMPORTANT" if threshold in (30,70,80) else "WATCH", previous.rsi14, current.rsi14, f"RSI14 {'向上' if direction=='UP' else '向下'}穿越 {threshold}。")
    if None not in (previous.ma5,previous.ma20,current.ma5,current.ma20):
        old, new = previous.ma5-previous.ma20, current.ma5-current.ma20
        direction = _crossed(old,new,0)
        if direction: add(f"MA5_MA20_CROSS_{direction}", "WATCH", f"{old:.4f}", f"{new:.4f}", "MA5 與 MA20 發生交叉。")
    for window in (20,60):
        old_ma, new_ma = getattr(previous,f"ma{window}"), getattr(current,f"ma{window}")
        if None not in (old_ma,new_ma):
            direction = _crossed(previous.close-old_ma,current.close-new_ma,0)
            if direction: add(f"PRICE_MA{window}_CROSS_{direction}", "WATCH", previous.close, current.close, f"收盤價{'站上' if direction=='UP' else '跌破'} MA{window}。")
    if current.latest_pivot_type:
        add(f"NEW_{current.latest_pivot_type}", "IMPORTANT", previous.latest_pivot_type or "NONE", current.latest_pivot_type, f"新 {current.latest_pivot_type} 於本日確認。")
    if previous.support_1 is not None:
        if previous.close >= previous.support_1 > current.close: add("SUPPORT_BROKEN", "CRITICAL", previous.support_1, current.close, "收盤價跌破前一日第一支撐。")
        if previous.close < previous.support_1 <= current.close: add("SUPPORT_RECLAIMED", "IMPORTANT", previous.close, current.close, "收盤價重新站回前一日第一支撐。")
    if previous.resistance_1 is not None:
        if previous.close <= previous.resistance_1 < current.close: add("RESISTANCE_BROKEN", "IMPORTANT", previous.resistance_1, current.close, "收盤價突破前一日第一壓力。")
        if previous.close > previous.resistance_1 >= current.close: add("RESISTANCE_FAILED_BREAKOUT", "WATCH", previous.close, current.close, "收盤價跌回前一日第一壓力之下。")
    for field,label in (("foreign_5d","FOREIGN_5D"),("trust_5d","TRUST_5D")):
        old,new=getattr(previous,field),getattr(current,field)
        if None not in (old,new) and ((old < 0 <= new) or (old > 0 >= new)):
            add(f"{label}_SIGN_CHANGED", "WATCH", old, new, f"{label} 累計值改變正負方向。")
    direction = _crossed(previous.margin_change_pct_20d,current.margin_change_pct_20d,20)
    if direction: add(f"MARGIN_ACCELERATION_{direction}", "IMPORTANT" if direction=="UP" else "INFO", previous.margin_change_pct_20d,current.margin_change_pct_20d,"融資 20 日增幅穿越 20% 警戒線。")
    direction = _crossed(previous.volume_ratio_20,current.volume_ratio_20,1.5)
    if direction: add(f"VOLUME_RATIO_1_5_{direction}", "WATCH", previous.volume_ratio_20,current.volume_ratio_20,"成交量比穿越 1.5 倍門檻。")
    return events


def changed_tickers(events, market_date, meaningful_only=True):
    severities = {"WATCH","IMPORTANT","CRITICAL"} if meaningful_only else {"INFO","WATCH","IMPORTANT","CRITICAL"}
    return sorted({event.ticker for event in events if event.market_date == market_date and event.severity in severities})
