from src.models import InstitutionalDaily, MarginDaily


def integer(value):
    text = str(value).strip().replace(",", "")
    if text in {"", "--", "---", "N/A"}:
        return None
    return int(text)


def normalize_institutional(ticker, market_date, envelope):
    payload = envelope["payload"]
    fields = payload.get("fields", [])
    required = ["證券代號", "外陸資買賣超股數(不含外資自營商)", "外資自營商買賣超股數", "投信買賣超股數",
                "自營商買賣超股數", "三大法人買賣超股數"]
    if not all(field in fields for field in required):
        raise ValueError("Unexpected TWSE institutional schema")
    matches = [dict(zip(fields, row)) for row in payload.get("data", []) if row and row[0].strip() == ticker]
    if len(matches) != 1:
        raise ValueError(f"Expected one institutional row for {ticker} on {market_date}; got {len(matches)}")
    row = matches[0]
    values = {field: integer(row[field]) for field in required[1:]}
    if any(value is None for value in values.values()):
        raise ValueError("Missing institutional value")
    return InstitutionalDaily(ticker=ticker, market_date=market_date,
        foreign_net=values[required[1]] + values[required[2]], investment_trust_net=values[required[3]],
        dealer_net=values[required[4]], institutional_total_net=values[required[5]],
        source=envelope["source"], retrieved_at=envelope["retrieved_at"])


def normalize_margin(ticker, market_date, envelope):
    tables = envelope["payload"].get("tables", [])
    candidates = [table for table in tables if table.get("fields") and table["fields"][0] == "代號"]
    if len(candidates) != 1:
        raise ValueError("Unexpected TWSE margin schema")
    table = candidates[0]
    if len(table["fields"]) != 16 or table["fields"][:8] != ["代號", "名稱", "買進", "賣出", "現金償還", "前日餘額", "今日餘額", "次一營業日限額"]:
        raise ValueError("Unexpected TWSE margin fields")
    matches = [row for row in table.get("data", []) if row and row[0].strip() == ticker]
    if len(matches) != 1:
        raise ValueError(f"Expected one margin row for {ticker} on {market_date}; got {len(matches)}")
    row = matches[0]
    # 融券欄位仍沿用表頭「買進、賣出」：買進是回補，賣出是新增融券。
    values = [integer(row[index]) for index in (2, 3, 4, 6, 9, 8, 10, 12)]
    if any(value is None or value < 0 for value in values):
        raise ValueError("Missing or negative margin value")
    previous_margin, previous_short = integer(row[5]), integer(row[11])
    if previous_margin + values[0] - values[1] - values[2] != values[3]:
        raise ValueError("TWSE margin balance reconciliation failed")
    if previous_short + values[4] - values[5] - values[6] != values[7]:
        raise ValueError("TWSE short balance reconciliation failed")
    return MarginDaily(ticker=ticker, market_date=market_date,
        margin_buy=values[0], margin_sell=values[1], margin_cash_repayment=values[2], margin_balance=values[3],
        short_sell=values[4], short_cover=values[5], short_stock_repayment=values[6], short_balance=values[7],
        source=envelope["source"], retrieved_at=envelope["retrieved_at"], source_note=row[15].strip())
