import csv
from datetime import date
from pathlib import Path

from src.charts.stock_chart import stock_chart
from src.database.db import frame
from src.indicators.core import calculate


def test_ten_manually_locked_source_dates(real_rows):
    rows = {r.market_date: r for r in real_rows}
    with (Path(__file__).parent / "fixtures/3702_verified_10.csv").open() as handle:
        expected = list(csv.DictReader(handle))
    assert len(expected) == 10
    for item in expected:
        row = rows[date.fromisoformat(item["market_date"])]
        for field in ("open", "high", "low", "close", "volume", "turnover"):
            assert getattr(row, field) == float(item[field])


def test_chart_exact_hover_and_shared_dates(real_rows):
    data = calculate(frame(real_rows))
    data["foreign_net"] = range(len(data))
    data["investment_trust_net"] = 0
    data["dealer_net"] = 0
    data["margin_balance"] = range(1000, 1000 + len(data))
    data["margin_change_1d"] = data.margin_balance.diff()
    fig = stock_chart(data, "20D")
    assert len(fig.data) == 12
    assert len(fig.data[0].x) == 20
    assert all(list(t.x) == list(fig.data[0].x) for t in fig.data)
    assert "成交量 8,678,579 股" in fig.data[0].text[0]
    assert "成交金額 1,018,289,884 元" in fig.data[0].text[0]
    assert fig.layout.hovermode == "x unified"
    assert all(t.xaxis == "x" for t in fig.data)
    assert list(fig.layout.xaxis.range) == ["2026-08-03", "2026-09-01"]
    assert all(s.xref == "paper" for s in fig.layout.shapes)
    assert fig.data[4].textposition == "none"
    assert {s.y0 for s in fig.layout.shapes} == {30, 50, 70}
