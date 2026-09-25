from datetime import date

from src.models import OHLCV

REQUIRED_FIELDS = ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價"]


def number(value, integer=False):
    text = str(value).strip().replace(",", "")
    if text in {"", "--", "---", "N/A"}:
        return None
    return int(text) if integer else float(text)


def normalize(ticker: str, envelope: dict) -> list[OHLCV]:
    payload = envelope["payload"]
    if not all(field in payload["fields"] for field in REQUIRED_FIELDS):
        raise ValueError("Unexpected TWSE schema; required fields missing")
    result = []
    for raw in payload["data"]:
        if len(raw) != len(payload["fields"]):
            raise ValueError("TWSE row length differs from schema")
        row = dict(zip(payload["fields"], raw))
        year, month, day = map(int, row["日期"].split("/"))
        result.append(OHLCV(ticker=ticker, market_date=date(year + 1911, month, day),
            open=number(row["開盤價"]), high=number(row["最高價"]), low=number(row["最低價"]), close=number(row["收盤價"]),
            volume=number(row["成交股數"], True), turnover=number(row["成交金額"], True),
            source=envelope["source"], retrieved_at=envelope["retrieved_at"],
            source_note=" | ".join(str(row.get(k, "")) for k in ["漲跌價差", "註記"])) )
    return result
