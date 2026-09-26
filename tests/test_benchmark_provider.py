from datetime import date

from src.data.benchmark_normalizer import normalize_sector_classification, normalize_taiex


def test_official_taiex_month_normalizes_matching_ohlc_and_market_totals():
    envelope = {"source":"https://www.twse.com.tw/official", "retrieved_at":"2026-09-25T00:00:00+00:00",
        "payload":{"ohlc":{"data":[["115/09/24","48,075.39","48,117.54","47,754.72","48,024.60"]]},
                   "market":{"data":[["115/09/24","8,100,000,000","700,000,000,000","1","48,024.60","-1"]]}}}
    row = normalize_taiex(envelope)[0]
    assert row.market_date == date(2026,9,24) and row.close == 48024.60
    assert row.volume == 8_100_000_000 and row.turnover == 700_000_000_000
    assert row.is_official and row.price_unit == "index_points"


def test_sector_classification_starts_when_official_snapshot_becomes_available():
    envelope = {"source":"https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
        "retrieved_at":"2026-09-25T01:00:00+00:00",
        "payload":[{"出表日期":"1150925","公司代號":"3702","產業別":"29"}]}
    row = normalize_sector_classification(envelope, {"3702"})[0]
    assert row.sector == "TWSE-29"
    assert row.available_date == row.effective_from == date(2026,9,25)
