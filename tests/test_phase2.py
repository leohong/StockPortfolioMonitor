import json
import hashlib
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.analysis.phase2_metrics import calculate_phase2
from src.data.phase2_normalizer import normalize_institutional, normalize_margin
from src.data.phase2_validator import validate_phase2
from src.data.providers.twse_phase2 import fetch_daily

FIXTURES = Path(__file__).parent / "fixtures"
DAY = date(2026, 9, 24)


def envelope(name):
    return {"source": f"https://www.twse.com.tw/{name}", "retrieved_at": datetime.now(timezone.utc),
            "payload": json.loads((FIXTURES / name).read_text("utf-8"))}


def test_official_phase2_regression_values_and_units():
    inst = normalize_institutional("3702", DAY, envelope("3702_20260924_institutional.json"))
    margin = normalize_margin("3702", DAY, envelope("3702_20260924_margin.json"))
    assert (inst.foreign_net, inst.investment_trust_net, inst.dealer_net, inst.institutional_total_net) == (2858239, 414000, 179238, 3451477)
    assert inst.unit == "shares"
    assert (margin.margin_buy, margin.margin_sell, margin.margin_cash_repayment, margin.margin_balance) == (757, 517, 0, 13472)
    assert (margin.short_sell, margin.short_cover, margin.short_stock_repayment, margin.short_balance) == (6, 0, 0, 42)
    assert margin.unit == "trading_units"
    assert validate_phase2([inst], [margin], {DAY}).status == "PASS"


def test_phase2_schema_and_reconciliation_fail_closed():
    item = envelope("3702_20260924_margin.json")
    item["payload"]["tables"][1]["data"] = [row for row in item["payload"]["tables"][1]["data"] if row[0] == "3702"]
    item["payload"]["tables"][1]["data"][0][12] = "999"
    with pytest.raises(ValueError, match="reconciliation"):
        normalize_margin("3702", DAY, item)


def test_rolling_sums_and_margin_changes():
    inst = pd.DataFrame({"foreign_net": range(1, 26), "investment_trust_net": [2] * 25, "dealer_net": [-1] * 25})
    margin = pd.DataFrame({"margin_balance": [100 + i * 10 for i in range(25)]})
    actual_inst, actual_margin = calculate_phase2(inst, margin)
    assert actual_inst.foreign_3d.iloc[2] == 6
    assert actual_inst.foreign_20d.iloc[19] == 210
    assert actual_inst.investment_trust_5d.iloc[4] == 10
    assert actual_margin.margin_change_1d.iloc[1] == 10
    assert actual_margin.margin_change_5d.iloc[5] == 50
    assert actual_margin.margin_change_20d.iloc[20] == 200
    assert actual_margin.margin_change_pct_20d.iloc[20] == pytest.approx(200)


def test_verified_cache_hit_never_opens_network(tmp_path, monkeypatch):
    payload = (FIXTURES / "3702_20260924_institutional.json").read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    target = tmp_path / "institutional"
    target.mkdir()
    archive = target / f"20260924_{digest[:12]}.json"
    archive.write_bytes(payload)
    archive.with_name(f"{archive.stem}.metadata.json").write_text(json.dumps({
        "source": "https://www.twse.com.tw/rwd/zh/fund/T86?date=20260924",
        "source_type": "official_exchange", "is_official": True,
        "retrieved_at": "2026-09-25T00:00:00+00:00", "sha256": digest,
        "archive": str(archive),
    }), "utf-8")

    class NetworkMustNotOpen:
        def __init__(self, *args, **kwargs):
            raise AssertionError("cache hit attempted network access")

    monkeypatch.setattr("src.data.providers.twse_phase2.httpx.Client", NetworkMustNotOpen)
    result = fetch_daily("institutional", DAY, tmp_path)
    assert result["sha256"] == digest
    assert result["payload"]["date"] == "20260924"
