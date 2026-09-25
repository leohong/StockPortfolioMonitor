from datetime import date, datetime, timezone

import pytest

from src.config import Settings
from src.database.db import connect, persist_evidence
from src.models import Evidence
from src.services.review_service import compare_holdings, historical_review, load_timeline


def settings(tmp_path):
    return Settings(database=tmp_path/"review.duckdb",cache_dir=tmp_path/"cache")


def seed_snapshots(config):
    with connect(config.database) as db:
        for ticker,base in (("1111",100),("2222",200)):
            for i in range(22):
                db.execute("""INSERT INTO analysis_snapshots
                (ticker,market_date,close,market_stage,structure_state,rsi14,ma20,volume_ratio_20,
                 foreign_5d,foreign_20d,trust_5d,trust_20d,margin_change_pct_20d,support_1,resistance_1,
                 bullish_evidence_count,bearish_evidence_count,warning_count,data_quality_status,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [ticker,date(2026,1,1+i),base+i,"D_UPTREND","UPTREND_STRUCTURE",55,base+i-2,1.1,
                 10,20,5,10,3,base+i-5,base+i+5,3,1,0,"PASS",datetime(2026,1,1,tzinfo=timezone.utc)])


def test_timeline_and_side_by_side_comparison_from_saved_snapshots(tmp_path):
    config=settings(tmp_path); seed_snapshots(config)
    snapshots,events=load_timeline(config,"1111",date(2026,1,5),date(2026,1,10))
    assert len(snapshots)==6 and events.empty
    compared=compare_holdings(config,["1111","2222"])
    assert compared.ticker.tolist()==["1111","2222"]
    assert compared.return_20d_pct.notna().all()
    assert compared.distance_support_pct.notna().all()


@pytest.mark.parametrize("tickers",[["1111"],["1","2","3","4","5","6"],["1111","1111"]])
def test_compare_requires_two_to_five_unique_holdings(tmp_path,tickers):
    with pytest.raises(ValueError,match="2–5"):
        compare_holdings(settings(tmp_path),tickers)


def test_historical_review_rejects_future_evidence(tmp_path):
    config=settings(tmp_path); seed_snapshots(config)
    item=Evidence(ticker="1111",market_date=date(2026,1,22),factor="rsi",status="BULLISH",headline="RSI",
        current_value="55",observations=[],reasoning="test",source_dates=[date(2026,1,23)],updated_at=datetime.now(timezone.utc))
    with connect(config.database) as db: persist_evidence(db,"1111",[item])
    with pytest.raises(ValueError,match="future"):
        historical_review(config,"1111",date(2026,1,22))
