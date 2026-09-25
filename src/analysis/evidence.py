from __future__ import annotations

from datetime import datetime, timezone
import math

import pandas as pd

from src.models import Evidence

FACTORS = ("price_structure", "rsi", "moving_averages", "volume", "institutional", "margin", "support_resistance")


def _missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def _e(ticker, day, factor, status, headline, value, observations, reasoning, dates):
    return Evidence(ticker=ticker, market_date=day, factor=factor, status=status, headline=headline,
        current_value=value, observations=observations, reasoning=reasoning,
        source_dates=sorted(set(dates)), updated_at=datetime.now(timezone.utc))


def build_evidence(row, structure, levels) -> list[Evidence]:
    ticker, day = str(row.ticker), row.market_date
    if hasattr(day, "date"):
        day = day.date()
    out = []
    if structure is None or structure.state == "UNCONFIRMED":
        out.append(_e(ticker, day, "price_structure", "INSUFFICIENT_DATA", "價格結構尚未確認", "—", [], "尚無一組已確認的高點與低點比較。", []))
    else:
        status = {"UPTREND_STRUCTURE":"BULLISH", "DOWNTREND_STRUCTURE":"BEARISH",
                  "POSSIBLE_BASE":"NEUTRAL", "POSSIBLE_TOP":"WARNING", "RANGE":"NEUTRAL"}[structure.state]
        obs = [{"metric":"latest_high", "label":structure.high_label, "value":structure.high_price, "unit":"TWD", "date":str(structure.high_pivot_date)},
               {"metric":"latest_low", "label":structure.low_label, "value":structure.low_price, "unit":"TWD", "date":str(structure.low_pivot_date)}]
        dates = [x for x in (structure.high_pivot_date, structure.low_pivot_date) if x]
        out.append(_e(ticker, day, "price_structure", status, f"{structure.high_label} + {structure.low_label}", structure.state, obs, "以最近兩個已確認的同類轉折比較價格高低。", dates))

    rsi = getattr(row, "rsi14", None)
    if _missing(rsi):
        out.append(_e(ticker, day, "rsi", "INSUFFICIENT_DATA", "RSI 尚未形成", "—", [], "需要至少 14 個連續價格變動。", []))
    else:
        status, headline = (("WARNING", "RSI 過熱") if rsi >= 70 else ("WARNING", "RSI 超賣") if rsi <= 30 else
                            ("BULLISH", "RSI 位於強勢區") if rsi > 50 else ("BEARISH", "RSI 位於弱勢區") if rsi < 50 else ("NEUTRAL", "RSI 中性"))
        out.append(_e(ticker, day, "rsi", status, headline, f"{rsi:.2f}", [{"metric":"rsi14","value":float(rsi),"unit":"index"}], "依 Wilder RSI14 與 30、50、70 門檻判讀。", [day]))

    mas = [getattr(row, f"ma{x}", None) for x in (5,20,60)]
    if any(_missing(x) for x in mas):
        out.append(_e(ticker, day, "moving_averages", "INSUFFICIENT_DATA", "均線資料不足", "—", [], "需要至少 60 個交易日。", []))
    else:
        status, headline = (("BULLISH", "均線多頭排列") if mas[0] > mas[1] > mas[2] else
                            ("BEARISH", "均線空頭排列") if mas[0] < mas[1] < mas[2] else ("NEUTRAL", "均線交錯"))
        obs = [{"metric":f"ma{x}","value":float(v),"unit":"TWD"} for x,v in zip((5,20,60),mas)]
        out.append(_e(ticker, day, "moving_averages", status, headline, f"{mas[0]:.2f} / {mas[1]:.2f} / {mas[2]:.2f}", obs, "比較 MA5、MA20 與 MA60 的相對順序。", [day]))

    ratio = getattr(row, "volume_ratio_20", None)
    if _missing(ratio):
        out.append(_e(ticker, day, "volume", "INSUFFICIENT_DATA", "成交量基準不足", "—", [], "需要 20 日平均成交量。", []))
    else:
        status, headline = (("WARNING", "成交量顯著放大") if ratio >= 2 else ("NEUTRAL", "成交量高於均量") if ratio >= 1.2 else
                            ("NEUTRAL", "成交量接近均量") if ratio >= .8 else ("NEUTRAL", "成交量低於均量"))
        out.append(_e(ticker, day, "volume", status, headline, f"{ratio:.2f}×", [{"metric":"volume_ratio_20","value":float(ratio),"unit":"times"}], "成交量除以 20 日平均成交量；成交量本身不代表方向。", [day]))

    foreign = getattr(row, "foreign_5d", None)
    if _missing(foreign):
        out.append(_e(ticker, day, "institutional", "INSUFFICIENT_DATA", "法人資料不足", "—", [], "需要連續 5 日官方法人資料。", []))
    else:
        status = "BULLISH" if foreign > 0 else "BEARISH" if foreign < 0 else "NEUTRAL"
        headline = "外資近 5 日買超" if foreign > 0 else "外資近 5 日賣超" if foreign < 0 else "外資近 5 日持平"
        obs = [{"metric":name,"value":int(getattr(row,name)),"unit":"shares"} for name in ("foreign_5d","investment_trust_5d","dealer_5d") if not _missing(getattr(row,name,None))]
        out.append(_e(ticker, day, "institutional", status, headline, f"{foreign:+,.0f} 股", obs, "方向以外資 5 日累計為主，並列出投信與自營商交叉檢視。", [day]))

    margin_pct = getattr(row, "margin_change_pct_20d", None)
    margin_balance = getattr(row, "margin_balance", None)
    if _missing(margin_pct) or _missing(margin_balance):
        out.append(_e(ticker, day, "margin", "INSUFFICIENT_DATA", "融資資料不足", "—", [], "需要連續 20 日官方融資餘額。", []))
    else:
        status = "WARNING" if margin_pct >= 20 else "NEUTRAL"
        headline = "融資餘額快速增加" if margin_pct >= 20 else "融資變化未達警戒"
        obs = [{"metric":"margin_balance","value":int(margin_balance),"unit":"trading_units"}, {"metric":"margin_change_pct_20d","value":float(margin_pct),"unit":"%"}]
        out.append(_e(ticker, day, "margin", status, headline, f"20 日 {margin_pct:+.2f}%", obs, "20 日融資增幅達 20% 標示槓桿參與警訊；不等同買賣建議。", [day]))

    support = next((x for x in levels if x.level_type == "SUPPORT" and x.rank == 1), None)
    resistance = next((x for x in levels if x.level_type == "RESISTANCE" and x.rank == 1), None)
    if support is None or resistance is None:
        out.append(_e(ticker, day, "support_resistance", "INSUFFICIENT_DATA", "支撐壓力證據不足", "—", [], "需要可追溯來源的支撐與壓力各至少一級。", []))
    else:
        obs = [{"metric":"support_1","value":support.price,"unit":"TWD","derivation":support.derivation,"date":str(support.evidence_date)},
               {"metric":"resistance_1","value":resistance.price,"unit":"TWD","derivation":resistance.derivation,"date":str(resistance.evidence_date)}]
        out.append(_e(ticker, day, "support_resistance", "NEUTRAL", "價格位於支撐與壓力之間", f"{support.price:.2f}–{resistance.price:.2f} 元", obs, "價位由已確認轉折、均線、盤整或高量區推導；不合併為交易分數。", [support.evidence_date,resistance.evidence_date]))
    assert tuple(x.factor for x in out) == FACTORS
    return out
