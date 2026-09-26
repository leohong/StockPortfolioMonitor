from __future__ import annotations

from collections.abc import Mapping


MIGRATIONS: dict[int, str] = {
    7: """
        CREATE TABLE IF NOT EXISTS analysis_versions (
            analysis_version VARCHAR,
            ruleset_version VARCHAR,
            schema_version INTEGER,
            created_at TIMESTAMPTZ,
            git_commit VARCHAR,
            config_hash VARCHAR,
            deprecated BOOLEAN DEFAULT false,
            PRIMARY KEY (analysis_version, ruleset_version)
        );
        CREATE TABLE IF NOT EXISTS snapshot_v3_daily (
            ticker VARCHAR,
            market_date DATE,
            analysis_version VARCHAR,
            ruleset_version VARCHAR,
            data_quality_status VARCHAR,
            payload_json VARCHAR,
            created_at TIMESTAMPTZ,
            PRIMARY KEY (ticker, market_date, analysis_version, ruleset_version)
        );
    """,
}


def apply_migrations(connection, migrations: Mapping[int, str] | None = None) -> list[int]:
    """Apply ordered additive migrations atomically, one version at a time."""
    migrations = dict(MIGRATIONS if migrations is None else migrations)
    connection.execute("CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY)")
    applied = {row[0] for row in connection.execute("SELECT version FROM schema_version").fetchall()}
    completed = []
    for version in sorted(migrations):
        if version in applied:
            continue
        if version > 1 and version - 1 not in applied:
            raise RuntimeError(f"Cannot apply schema migration {version} before {version - 1}")
        connection.execute("BEGIN TRANSACTION")
        try:
            connection.execute(migrations[version])
            connection.execute("INSERT INTO schema_version VALUES (?)", [version])
            connection.execute("COMMIT")
            applied.add(version)
            completed.append(version)
        except Exception:
            connection.execute("ROLLBACK")
            raise
    return completed
