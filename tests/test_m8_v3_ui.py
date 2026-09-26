import csv,io,json
from datetime import date
import pandas as pd

from src.services.export_service import v3_snapshot_csv
from src.services.ui_v3_service import filter_v3_portfolio


def test_v3_portfolio_attention_filters_without_ranking():
    data=pd.DataFrame([
        {"ticker":"1111","name":"甲","market_state":"S4_TREND","highest_significance":"LOW","significant_change":True,"quality":"PASS"},
        {"ticker":"2222","name":"乙","market_state":"S8_STRUCTURE_FAILURE","highest_significance":"HIGH","significant_change":True,"quality":"PASS_WITH_WARNINGS"},
    ])
    result=filter_v3_portfolio(data,states=["S8_STRUCTURE_FAILURE"],attention="HIGH／CRITICAL",changed_only=True)
    assert result.ticker.tolist()==["2222"]
    assert filter_v3_portfolio(data,search="甲").ticker.tolist()==["1111"]


def test_v3_csv_reproduces_snapshot_events_and_scenarios():
    snapshot={"market_date":date(2026,9,24),"payload":{"market_state":"TRANSITION","evidence_vector":{"dimensions":{"trend":{"state":"TREND_EMERGING"}}}}}
    events=[{"dimension":"location","previous_state":"AT_SUPPORT","current_state":"NEAR_SUPPORT","significance":"MEDIUM"}]
    scenarios=[{"scenario_type":"NEUTRAL_UNRESOLVED","current_status":"SUPPORTED","conditions":[{"dimension":"market_state","satisfied":True}]}]
    rows=list(csv.reader(io.StringIO(v3_snapshot_csv(snapshot,events,scenarios).decode("utf-8-sig"))))
    text="\n".join(",".join(row) for row in rows)
    assert "TRANSITION" in text and "AT_SUPPORT -> NEAR_SUPPORT [MEDIUM]" in text
    assert "NEUTRAL_UNRESOLVED" in text and "market_state" in text
