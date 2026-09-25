from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from src.services.portfolio_service import filter_portfolio


def rows(count=3):
    return pd.DataFrame([{"ticker":f"{1000+i}","name":name,"stage":stage,"important_count":important,
        "changed":changed,"quality":quality} for i,(name,stage,important,changed,quality) in enumerate([
            ("甲公司","D_UPTREND",1,True,"PASS"),("乙公司","A_DOWNTREND",0,False,"PASS_WITH_WARNINGS"),
            ("丙公司","TRANSITION",0,True,"PASS")][:count])])


def test_portfolio_filters_search_stage_alert_and_changed_only():
    data = rows()
    assert filter_portfolio(data,search="1001").ticker.tolist() == ["1001"]
    assert filter_portfolio(data,search="甲").ticker.tolist() == ["1000"]
    assert filter_portfolio(data,stages=["TRANSITION"]).ticker.tolist() == ["1002"]
    assert filter_portfolio(data,alert="有重要警示").ticker.tolist() == ["1000"]
    assert filter_portfolio(data,alert="資料品質警告").ticker.tolist() == ["1001"]
    assert filter_portfolio(data,changed_only=True).ticker.tolist() == ["1000","1002"]


def test_filter_does_not_rank_or_reorder_rows():
    data = rows().iloc[[2,0,1]].reset_index(drop=True)
    assert filter_portfolio(data).ticker.tolist() == ["1002","1000","1001"]


@pytest.mark.parametrize("count", [0,101])
def test_portfolio_limit_rejected(count):
    from src.services.portfolio_service import load_portfolio
    with pytest.raises(ValueError,match="1–100"):
        load_portfolio(SimpleNamespace(), [SimpleNamespace(ticker=str(i)) for i in range(count)])


def test_one_hundred_holdings_use_one_database_query(monkeypatch):
    calls = []
    class Result:
        def fetchdf(self): return pd.DataFrame()
    class Database:
        def execute(self, query, params): calls.append((query,params)); return Result()
    class Context:
        def __enter__(self): return Database()
        def __exit__(self,*args): pass
    monkeypatch.setattr("src.services.portfolio_service.connect", lambda path: Context())
    holdings = [SimpleNamespace(ticker=f"{i:04d}",name=f"股票{i}",cost=None) for i in range(100)]
    from src.services.portfolio_service import load_portfolio
    result = load_portfolio(SimpleNamespace(database="memory"),holdings)
    assert len(result) == 100
    assert len(calls) == 1
    assert len(calls[0][1]) == 100
