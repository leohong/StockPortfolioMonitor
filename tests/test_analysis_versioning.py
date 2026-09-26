from datetime import datetime, timezone

import pytest

from src.analysis.versioning import config_hash, register_analysis_version, version_record
from src.database.db import connect


def test_config_hash_is_deterministic_and_order_independent():
    assert config_hash({"b": 2, "a": 1}) == config_hash({"a": 1, "b": 2})
    assert len(config_hash({"a": 1})) == 64


def test_analysis_version_registration_is_idempotent_and_identity_is_immutable(tmp_path):
    created = datetime(2026, 9, 26, tzinfo=timezone.utc)
    version = version_record("404b40e", {"pivot_left": 3}, created_at=created)
    with connect(tmp_path / "versions.duckdb") as db:
        register_analysis_version(db, version)
        register_analysis_version(db, version)
        assert db.execute("SELECT count(*) FROM analysis_versions").fetchone()[0] == 1
        changed = version.model_copy(update={"git_commit": "fffffff"})
        with pytest.raises(ValueError, match="immutable"):
            register_analysis_version(db, changed)
