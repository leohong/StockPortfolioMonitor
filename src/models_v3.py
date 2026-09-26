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


class TrendQuality(BaseModel):
    ticker: str
    market_date: date
    state: Literal["TREND_EMERGING", "TREND_HEALTHY", "TREND_EXTENDED", "TREND_DECELERATING", "TREND_BROKEN", "RANGE", "INSUFFICIENT_DATA"]
    ma5: float | None = None
    ma20: float | None = None
    ma60: float | None = None
    ma120: float | None = None
    ma20_slope_5d_pct: float | None = None
    ma60_slope_5d_pct: float | None = None
    ma120_slope_5d_pct: float | None = None
    distance_ma20_pct: float | None = None
    distance_ma60_pct: float | None = None
    ma20_ma60_separation_pct: float | None = None
    persistence_20d: float | None = None
    observations: list[dict[str, Any]] = Field(default_factory=list)
    source_dates: list[date] = Field(default_factory=list)
    analysis_version: Literal["v3"] = "v3"
    ruleset_version: str
    created_at: datetime


class MomentumState(BaseModel):
    ticker: str
    market_date: date
    state: Literal["ACCELERATING", "POSITIVE", "COOLING", "NEUTRAL", "WEAKENING", "NEGATIVE", "RESET", "INSUFFICIENT_DATA"]
    rsi14: float | None = None
    rsi_change_5d: float | None = None
    roc20: float | None = None
    rsi_cross: str | None = None
    divergence: Literal["BULLISH", "BEARISH"] | None = None
    divergence_pivot_date: date | None = None
    divergence_confirmation_date: date | None = None
    observations: list[dict[str, Any]] = Field(default_factory=list)
    source_dates: list[date] = Field(default_factory=list)
    analysis_version: Literal["v3"] = "v3"
    ruleset_version: str
    created_at: datetime


class RelativeStrengthState(BaseModel):
    ticker: str
    market_date: date
    benchmark_symbol: str = "TAIEX"
    benchmark_date: date | None = None
    rs_line: float | None = None
    rs_line_indexed: float | None = None
    rs_market_20d: float | None = None
    rs_market_60d: float | None = None
    rs_market_120d: float | None = None
    rs_line_change_20d: float | None = None
    state: Literal["LEADING", "IMPROVING", "NEUTRAL", "WEAKENING", "LAGGING", "INSUFFICIENT_DATA"]
    rs_sector_20d: float | None = None
    sector_state: str = "INSUFFICIENT_DATA"
    missing_inputs: list[str] = Field(default_factory=list)
    price_basis: Literal["UNADJUSTED"] = "UNADJUSTED"
    corporate_action_warning: bool = False
    source_dates: list[date] = Field(default_factory=list)
    analysis_version: Literal["v3"] = "v3"
    ruleset_version: str
    created_at: datetime
