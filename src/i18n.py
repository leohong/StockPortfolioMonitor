"""繁體中文顯示文字；資料庫欄位與狀態代碼維持穩定。"""

STATUS = {"PASS": "通過", "PASS_WITH_WARNINGS": "通過（含警告）", "FAIL": "未通過"}
RANGE_LABELS = {"20D": "20 個交易日", "60D": "60 個交易日", "120D": "120 個交易日", "1Y": "近一年"}
FIELDS = {
    "ticker": "股票代號", "market_date": "交易日期", "open": "開盤價", "high": "最高價",
    "low": "最低價", "close": "收盤價", "volume": "成交股數", "turnover": "成交金額（新臺幣）",
    "source": "資料來源", "source_type": "來源類型", "is_official": "官方來源",
    "retrieved_at": "擷取時間", "volume_unit": "成交量單位", "turnover_unit": "成交金額單位",
    "source_note": "來源註記", "ma5": "5 日均線", "ma20": "20 日均線", "ma60": "60 日均線",
    "rsi14": "相對強弱指標 RSI14", "volume_ma20": "20 日均量（股）", "volume_ratio_20": "20 日量比",
}
MESSAGES = {
    "No OHLCV rows": "尚無開高低收與成交量資料",
    "Duplicate market dates": "交易日期重複", "Market dates not ordered": "交易日期未依序排列",
    "Mixed tickers": "資料混有不同股票代號", "future market date": "交易日期晚於檢查日期",
    "missing/nonfinite/nonpositive OHLC": "開高低收有缺值、非有限數值或非正數",
    "invalid OHLC bounds": "開盤價或收盤價超出最高價與最低價範圍",
    "invalid volume/turnover": "成交量或成交金額無效", "unknown units": "單位不明",
    "invalid provenance": "來源資訊或擷取時間無效",
    "zero volume; confirm trading status": "成交量為零，請確認交易狀態",
    "source marks ex-right/dividend or price adjustment; raw unadjusted series": "官方資料標示除權息或價格調整；目前使用未還原權息價格",
    "Stale data: latest session": "資料可能過期，最新交易日為",
    "suspicious price discontinuity (>11%); review corporate actions": "價格變動超過 11%，請核對除權息或其他公司行動",
    "Missing sessions unverified: official exchange calendar not integrated; holidays are not fabricated": "尚未整合官方交易日曆，無法完整確認缺漏交易日；不會自行補入休市日資料",
    "Missing expected sessions:": "缺漏的預期交易日：",
    "Corporate actions not fully verified (dividends, splits, capital reductions/increases); prices are unadjusted": "尚未完整核對股利、股票分割、減資與增資；目前價格未還原權息",
    "Single official source: cross-source conflicts not independently checked": "目前僅使用單一官方來源，尚未獨立比對不同來源的差異",
    "Official source revision": "官方資料修訂", "old=": "原值＝", "new=": "新值＝",
}


def message(text):
    for original, translated in MESSAGES.items():
        text = text.replace(original, translated)
    return text


def display_value(value):
    if value is True:
        return "是"
    if value is False:
        return "否"
    return {"shares": "股", "TWD": "新臺幣", "official_exchange": "證券交易所官方資料"}.get(str(value), str(value))
