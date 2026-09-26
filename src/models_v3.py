from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AnalysisVersion(BaseModel):
    model_config = ConfigDict(frozen=True)

    analysis_version: str = Field(pattern=r"^v\d+$")
    ruleset_version: str = Field(min_length=1)
    schema_version: int = Field(ge=1)
    created_at: datetime
    git_commit: str = Field(min_length=7)
    config_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    deprecated: bool = False


class V3SnapshotEnvelope(BaseModel):
    """Versioned storage envelope only; M1 defines no V3 analytical fields."""

    model_config = ConfigDict(frozen=True)

    ticker: str = Field(pattern=r"^\d{4,6}$")
    market_date: date
    analysis_version: Literal["v3"] = "v3"
    ruleset_version: str = Field(min_length=1)
    data_quality_status: Literal["PASS", "PASS_WITH_WARNINGS", "FAIL"]
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class BenchmarkDaily(BaseModel):
    symbol: Literal["TAIEX"] = "TAIEX"
    market_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    turnover: int
    source: str
    source_type: Literal["official_exchange"] = "official_exchange"
    is_official: bool = True
    retrieved_at: datetime
    price_unit: Literal["index_points"] = "index_points"
    volume_unit: Literal["shares"] = "shares"


class SectorClassification(BaseModel):
    ticker: str = Field(pattern=r"^\d{4,6}$")
    sector: str
    industry: str
    classification_source: str
    retrieved_at: datetime
    available_date: date
    effective_from: date
    effective_to: date | None = None


class RegimeEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    context_type: Literal["MARKET", "SECTOR"]
    context_id: str
    market_date: date
    regime: Literal["RISK_ON_TREND", "RISK_ON_EXTENDED", "RANGE_ROTATION", "RISK_OFF", "TRANSITION", "INSUFFICIENT_DATA"]
    confidence_class: Literal["CONFIRMED", "MIXED", "TENTATIVE", "INSUFFICIENT"]
    evidence_for: list[dict[str, Any]] = Field(default_factory=list)
    evidence_against: list[dict[str, Any]] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    source_dates: list[date] = Field(default_factory=list)
    analysis_version: Literal["v3"] = "v3"
    ruleset_version: str
    created_at: datetime
