from datetime import date, timedelta

import pandas as pd
import pytest

from src.analysis.flow import calculate_capital_flow
from src.analysis.participation import calculate_participation
from src.analysis.positioning import calculate_positioning


RULES="m4-test"


def stock(count=25):
    days=[date(2026,1,1)+timedelta(days=i) for i in range(count)]
    return pd.DataFrame({"ticker":"3702","market_date":days,"open":100.,"high":[101+i*.1 for i in range(count)],
        "low":[99+i*.1 for i in range(count)],"close":[100+i*.1 for i in range(count)],
        "volume":[1000]*count,"turnover":[100000]*count})


def test_participation_uses_prior_range_and_configurable_thresholds():
    data=stock(); data.loc[24,["high","close","volume"]]=[110,109.8,2000]
    result=calculate_participation(data,RULES,strong_ratio=1.5)[-1]
    assert result.state=="STRONG_CONFIRMATION"
    assert result.breakout is True and result.volume_ratio_20 > 1.5
    assert result.volume_unit=="shares" and len(result.source_dates)==21
    assert calculate_participation(data,RULES,strong_ratio=3,confirm_ratio=2.5)[-1].state=="WEAK_CONFIRMATION"


def test_high_volume_alone_is_abnormal_not_distribution():
    data=stock(); data.loc[24,"volume"]=4000
    result=calculate_participation(data,RULES,abnormal_ratio=2.5)[-1]
    assert result.state=="ABNORMAL"
    assert "distribution" not in result.model_dump_json().lower()


def test_flow_persistence_and_reversal_are_participant_specific():
    days=[date(2026,1,1)+timedelta(days=i) for i in range(20)]
    frame=pd.DataFrame({"ticker":"3702","market_date":days,"foreign_net":[10]*20,
        "investment_trust_net":[-5]*17+[20]*3,"dealer_net":[0]*20})
    latest={item.participant:item for item in calculate_capital_flow(frame,RULES) if item.market_date==days[-1]}
    assert latest["FOREIGN"].state=="PERSISTENT_BUYING" and latest["FOREIGN"].net_flow_20d==200
    assert latest["INVESTMENT_TRUST"].state=="REVERSING_POSITIVE"
    assert latest["DEALER"].state=="NEUTRAL"
    assert all(item.unit=="shares" for item in latest.values())


def test_positioning_leverage_divergence_and_units():
    prices=stock()
    margins=pd.DataFrame({"ticker":"3702","market_date":prices.market_date,
        "margin_balance":[1000+i*15 for i in range(25)],"short_balance":[100+i for i in range(25)]})
    result=calculate_positioning(prices,margins,RULES,expansion_pct=10,crowded_pct=20)[-1]
    expected=(margins.margin_balance.iloc[-1]/margins.margin_balance.iloc[-21]-1)*100-(prices.close.iloc[-1]/prices.close.iloc[-21]-1)*100
    assert result.leverage_divergence_20d==pytest.approx(expected)
    assert result.state in {"LEVERAGE_EXPANDING","CROWDED"}
    assert result.balance_unit=="trading_units" and len(result.source_dates)==21
