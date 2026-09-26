from __future__ import annotations

from datetime import date, datetime

from src.models_v3 import BenchmarkDaily, SectorClassification


def _number(value, integer=False):
    parsed = float(str(value).replace(",", ""))
    return int(parsed) if integer else parsed


def _roc_date(value: str) -> date:
    year, month, day = map(int, value.split("/"))
    return date(year + 1911, month, day)


def _official_report_date(value: str) -> date:
    text = value.strip()
    if len(text) == 7 and text.isdigit():
        return date(int(text[:3]) + 1911, int(text[3:5]), int(text[5:7]))
    return datetime.strptime(text, "%Y%m%d").date()


def normalize_taiex(envelope: dict) -> list[BenchmarkDaily]:
    payload = envelope["payload"]
    market = {_roc_date(row[0]): row for row in payload["market"]["data"]}
    output = []
    for row in payload["ohlc"]["data"]:
        day = _roc_date(row[0])
        if day not in market:
            raise ValueError(f"TAIEX OHLC lacks matching market totals on {day}")
        totals = market[day]
        output.append(BenchmarkDaily(market_date=day, open=_number(row[1]), high=_number(row[2]),
            low=_number(row[3]), close=_number(row[4]), volume=_number(totals[1], True),
            turnover=_number(totals[2], True), source=envelope["source"], retrieved_at=envelope["retrieved_at"]))
    return output


def normalize_sector_classification(envelope: dict, tickers: set[str] | None = None) -> list[SectorClassification]:
    output = []
    for row in envelope["payload"]:
        ticker = str(row.get("公司代號", "")).strip()
        if not ticker or (tickers is not None and ticker not in tickers):
            continue
        available = _official_report_date(str(row["出表日期"]))
        industry = str(row.get("產業別", "")).strip() or "UNKNOWN"
        output.append(SectorClassification(ticker=ticker, sector=f"TWSE-{industry}", industry=industry,
            classification_source=envelope["source"], retrieved_at=envelope["retrieved_at"],
            available_date=available, effective_from=available))
    return output
