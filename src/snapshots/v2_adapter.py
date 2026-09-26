from __future__ import annotations

from dataclasses import dataclass

from src.models import AnalysisSnapshot


@dataclass(frozen=True)
class V2SnapshotArtifact:
    snapshot: AnalysisSnapshot
    analysis_version: str = "v2"
    ruleset_version: str = "legacy-unversioned"


def as_v2_artifact(snapshot: AnalysisSnapshot) -> V2SnapshotArtifact:
    """Label a legacy snapshot in memory without rewriting historical rows."""
    return V2SnapshotArtifact(snapshot=snapshot)
