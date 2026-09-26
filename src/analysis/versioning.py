from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.models_v3 import AnalysisVersion


V3_ANALYSIS_VERSION = "v3"
V3_RULESET_VERSION = "m2-regime-v1"
V3_SCHEMA_VERSION = 8


def config_hash(value: Any) -> str:
    """Return a stable SHA256 for the configuration that produced analysis."""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    elif isinstance(value, Path):
        value = value.read_text("utf-8")
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def version_record(git_commit: str, configuration: Any, *, created_at: datetime | None = None) -> AnalysisVersion:
    return AnalysisVersion(
        analysis_version=V3_ANALYSIS_VERSION,
        ruleset_version=V3_RULESET_VERSION,
        schema_version=V3_SCHEMA_VERSION,
        created_at=created_at or datetime.now(timezone.utc),
        git_commit=git_commit,
        config_hash=config_hash(configuration),
    )


def register_analysis_version(connection, version: AnalysisVersion) -> None:
    values = version.model_dump()
    existing = connection.execute(
        "SELECT schema_version,git_commit,config_hash,deprecated FROM analysis_versions WHERE analysis_version=? AND ruleset_version=?",
        [version.analysis_version, version.ruleset_version],
    ).fetchone()
    identity = (version.schema_version, version.git_commit, version.config_hash, version.deprecated)
    if existing is not None and tuple(existing) != identity:
        raise ValueError("Analysis version identity is immutable")
    if existing is None:
        connection.execute(
            "INSERT INTO analysis_versions VALUES (?,?,?,?,?,?,?)",
            [values[name] for name in ("analysis_version", "ruleset_version", "schema_version", "created_at", "git_commit", "config_hash", "deprecated")],
        )
