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
