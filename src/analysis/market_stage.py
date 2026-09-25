from __future__ import annotations

from datetime import datetime, timezone
import math

from src.models import MarketStage


def _missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def classify_stage(row, structure, evidence, previous_row=None, previous_stage=None) -> MarketStage:
    day = row.market_date.date() if hasattr(row.market_date, "date") else row.market_date
    ticker = str(row.ticker)
    required = (getattr(row, "close", None), getattr(row, "ma5", None), getattr(row, "ma20", None), getattr(row, "rsi14", None))
    factors = [item.factor for item in evidence if item.status != "INSUFFICIENT_DATA"]
    reasons = []
    if structure is None or structure.state == "UNCONFIRMED" or any(_missing(value) for value in required):
        reasons.append("價格結構、MA5、MA20 或 RSI14 尚未具備完整證據")
        stage = "UNCLASSIFIED"
    else:
        close, ma5, ma20, rsi = map(float, required)
        ma20_prev = getattr(previous_row, "ma20", None) if previous_row else None
        rsi_prev = getattr(previous_row, "rsi14", None) if previous_row else None
        margin_pct = getattr(row, "margin_change_pct_20d", None)
        volume_ratio = getattr(row, "volume_ratio_20", None)
        foreign_5d = getattr(row, "foreign_5d", None)
        deviation = (close / ma20 - 1) * 100
        overheated = rsi >= 70 and deviation >= 8 and ((not _missing(volume_ratio) and volume_ratio >= 1.3) or (not _missing(margin_pct) and margin_pct >= 20))
        correction = previous_stage == "E_OVERHEATED" and rsi < 70 and close < ma5
        weakening = structure.state == "DOWNTREND_STRUCTURE" and close < ma20 and not _missing(foreign_5d) and foreign_5d < 0 and previous_stage in {"D_UPTREND","E_OVERHEATED","F_HIGH_LEVEL_CORRECTION","G_STRUCTURE_WEAKENING"}
        downtrend = structure.state == "DOWNTREND_STRUCTURE" and close < ma20
        early_base = structure.state == "POSSIBLE_BASE" or (structure.state == "DOWNTREND_STRUCTURE" and not _missing(rsi_prev) and rsi > rsi_prev and rsi < 50)
        base_confirmation = structure.state == "POSSIBLE_BASE" and close > ma5 and rsi > 50 and structure.low_label == "HL"
        uptrend = structure.state == "UPTREND_STRUCTURE" and ma5 > ma20 and (ma20_prev is None or _missing(ma20_prev) or ma20 >= ma20_prev) and 50 <= rsi < 70
        if overheated:
            stage = "E_OVERHEATED"; reasons += [f"RSI14 {rsi:.2f} ≥ 70", f"收盤價高於 MA20 {deviation:.2f}%"]
            if not _missing(volume_ratio) and volume_ratio >= 1.3: reasons.append(f"量比 {volume_ratio:.2f}× ≥ 1.30×")
            if not _missing(margin_pct) and margin_pct >= 20: reasons.append(f"融資 20 日增加 {margin_pct:.2f}%")
        elif correction:
            stage = "F_HIGH_LEVEL_CORRECTION"; reasons += ["前一交易日為過熱階段", f"RSI14 回落至 {rsi:.2f}", f"收盤價 {close:.2f} 跌破 MA5 {ma5:.2f}"]
        elif weakening:
            stage = "G_STRUCTURE_WEAKENING"; reasons += [f"結構為 {structure.high_label}+{structure.low_label}", f"收盤價 {close:.2f} 低於 MA20 {ma20:.2f}", f"外資 5 日賣超 {foreign_5d:,.0f} 股"]
        elif downtrend:
            stage = "A_DOWNTREND"; reasons += [f"結構為 {structure.high_label}+{structure.low_label}", f"收盤價 {close:.2f} 低於 MA20 {ma20:.2f}"]
        elif base_confirmation:
            stage = "C_BASE_CONFIRMATION"; reasons += [f"已確認較高低點 HL {structure.low_price:.2f}", f"收盤價 {close:.2f} 高於 MA5 {ma5:.2f}", f"RSI14 {rsi:.2f} > 50"]
        elif early_base:
            stage = "B_EARLY_BASE"; reasons += [f"結構狀態為 {structure.state}", f"RSI14 {rsi:.2f}"]
            if not _missing(rsi_prev): reasons.append(f"前一日 RSI14 {rsi_prev:.2f}")
        elif uptrend:
            stage = "D_UPTREND"; reasons += [f"結構為 {structure.high_label}+{structure.low_label}", f"MA5 {ma5:.2f} 高於 MA20 {ma20:.2f}", f"RSI14 {rsi:.2f} 位於 50–70"]
        else:
            stage = "TRANSITION"; reasons += [f"結構狀態為 {structure.state}", "目前證據未同時滿足任一明確階段"]
    return MarketStage(ticker=ticker, market_date=day, stage=stage, reasons=reasons,
        evidence_factors=factors, created_at=datetime.now(timezone.utc))
