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
    8: """
        CREATE TABLE IF NOT EXISTS benchmark_daily (
            symbol VARCHAR, market_date DATE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
            volume BIGINT, turnover BIGINT, source VARCHAR, source_type VARCHAR, is_official BOOLEAN,
            retrieved_at TIMESTAMPTZ, price_unit VARCHAR, volume_unit VARCHAR,
            PRIMARY KEY (symbol, market_date)
        );
        CREATE TABLE IF NOT EXISTS sector_classification (
            ticker VARCHAR, sector VARCHAR, industry VARCHAR, classification_source VARCHAR,
            retrieved_at TIMESTAMPTZ, available_date DATE, effective_from DATE, effective_to DATE,
            PRIMARY KEY (ticker, effective_from)
        );
        CREATE TABLE IF NOT EXISTS sector_benchmark_daily (
            sector VARCHAR, symbol VARCHAR, market_date DATE, open DOUBLE, high DOUBLE, low DOUBLE,
            close DOUBLE, volume BIGINT, source VARCHAR, source_type VARCHAR, is_official BOOLEAN,
            retrieved_at TIMESTAMPTZ, PRIMARY KEY (sector, symbol, market_date)
        );
        CREATE TABLE IF NOT EXISTS market_breadth_daily (
            market VARCHAR, market_date DATE, advancing_count INTEGER, declining_count INTEGER,
            unchanged_count INTEGER, new_high_count INTEGER, new_low_count INTEGER,
            pct_above_ma20 DOUBLE, pct_above_ma60 DOUBLE, source VARCHAR, retrieved_at TIMESTAMPTZ,
            available_date DATE, PRIMARY KEY (market, market_date)
        );
        CREATE TABLE IF NOT EXISTS regime_daily (
            context_type VARCHAR, context_id VARCHAR, market_date DATE, regime VARCHAR,
            confidence_class VARCHAR, evidence_for_json VARCHAR, evidence_against_json VARCHAR,
            missing_inputs_json VARCHAR, source_dates_json VARCHAR, analysis_version VARCHAR,
            ruleset_version VARCHAR, created_at TIMESTAMPTZ,
            PRIMARY KEY (context_type, context_id, market_date, analysis_version, ruleset_version)
        );
    """,
    9: """
        CREATE TABLE IF NOT EXISTS trend_quality_daily (
            ticker VARCHAR, market_date DATE, state VARCHAR,
            ma5 DOUBLE, ma20 DOUBLE, ma60 DOUBLE, ma120 DOUBLE,
            ma20_slope_5d_pct DOUBLE, ma60_slope_5d_pct DOUBLE, ma120_slope_5d_pct DOUBLE,
            distance_ma20_pct DOUBLE, distance_ma60_pct DOUBLE, ma20_ma60_separation_pct DOUBLE,
            persistence_20d DOUBLE, observations_json VARCHAR, source_dates_json VARCHAR,
            analysis_version VARCHAR, ruleset_version VARCHAR, created_at TIMESTAMPTZ,
            PRIMARY KEY (ticker, market_date, analysis_version, ruleset_version)
        );
        CREATE TABLE IF NOT EXISTS momentum_state_daily (
            ticker VARCHAR, market_date DATE, state VARCHAR, rsi14 DOUBLE, rsi_change_5d DOUBLE,
            roc20 DOUBLE, rsi_cross VARCHAR, divergence VARCHAR, divergence_pivot_date DATE,
            divergence_confirmation_date DATE, observations_json VARCHAR, source_dates_json VARCHAR,
            analysis_version VARCHAR, ruleset_version VARCHAR, created_at TIMESTAMPTZ,
            PRIMARY KEY (ticker, market_date, analysis_version, ruleset_version)
        );
        CREATE TABLE IF NOT EXISTS relative_strength_daily (
            ticker VARCHAR, market_date DATE, benchmark_symbol VARCHAR, benchmark_date DATE,
            rs_line DOUBLE, rs_line_indexed DOUBLE, rs_market_20d DOUBLE, rs_market_60d DOUBLE,
            rs_market_120d DOUBLE, rs_line_change_20d DOUBLE, state VARCHAR,
            rs_sector_20d DOUBLE, sector_state VARCHAR, missing_inputs_json VARCHAR,
            price_basis VARCHAR, corporate_action_warning BOOLEAN, source_dates_json VARCHAR,
            analysis_version VARCHAR, ruleset_version VARCHAR, created_at TIMESTAMPTZ,
            PRIMARY KEY (ticker, market_date, analysis_version, ruleset_version)
        );
    """,
    10: """
        CREATE TABLE IF NOT EXISTS participation_daily (
            ticker VARCHAR, market_date DATE, state VARCHAR, volume BIGINT, volume_ma5 DOUBLE,
            volume_ma20 DOUBLE, volume_ratio_20 DOUBLE, turnover BIGINT, close_location_value DOUBLE,
            breakout BOOLEAN, breakdown BOOLEAN, observations_json VARCHAR, missing_inputs_json VARCHAR,
            source_dates_json VARCHAR, volume_unit VARCHAR, turnover_unit VARCHAR, analysis_version VARCHAR,
            ruleset_version VARCHAR, created_at TIMESTAMPTZ,
            PRIMARY KEY (ticker, market_date, analysis_version, ruleset_version)
        );
        CREATE TABLE IF NOT EXISTS capital_flow_daily (
            ticker VARCHAR, market_date DATE, participant VARCHAR, state VARCHAR,
            net_flow_1d BIGINT, net_flow_3d BIGINT, net_flow_5d BIGINT, net_flow_10d BIGINT,
            net_flow_20d BIGINT, positive_days_10d INTEGER, negative_days_10d INTEGER,
            flow_persistence_10d DOUBLE, observations_json VARCHAR, missing_inputs_json VARCHAR,
            source_dates_json VARCHAR, unit VARCHAR, analysis_version VARCHAR, ruleset_version VARCHAR,
            created_at TIMESTAMPTZ,
            PRIMARY KEY (ticker, market_date, participant, analysis_version, ruleset_version)
        );
        CREATE TABLE IF NOT EXISTS positioning_daily (
            ticker VARCHAR, market_date DATE, state VARCHAR, margin_balance BIGINT,
            margin_change_5d BIGINT, margin_change_10d BIGINT, margin_change_20d BIGINT,
            margin_change_pct_5d DOUBLE, margin_change_pct_10d DOUBLE, margin_change_pct_20d DOUBLE,
            short_balance BIGINT, short_change_5d BIGINT, short_change_10d BIGINT, short_change_20d BIGINT,
            price_return_pct_20d DOUBLE, leverage_divergence_20d DOUBLE, turnover_ratio_20 DOUBLE,
            observations_json VARCHAR, missing_inputs_json VARCHAR, source_dates_json VARCHAR,
            balance_unit VARCHAR, analysis_version VARCHAR, ruleset_version VARCHAR, created_at TIMESTAMPTZ,
            PRIMARY KEY (ticker, market_date, analysis_version, ruleset_version)
        );
    """,
    11: """
        CREATE TABLE IF NOT EXISTS volatility_daily (
            ticker VARCHAR, market_date DATE, state VARCHAR, atr14 DOUBLE, atr14_pct DOUBLE,
            historical_volatility_20d DOUBLE, range_ratio DOUBLE, gap_pct DOUBLE,
            volatility_percentile DOUBLE, observations_json VARCHAR, missing_inputs_json VARCHAR,
            source_dates_json VARCHAR, analysis_version VARCHAR, ruleset_version VARCHAR, created_at TIMESTAMPTZ,
            PRIMARY KEY (ticker, market_date, analysis_version, ruleset_version)
        );
        CREATE TABLE IF NOT EXISTS anchored_vwap_daily (
            ticker VARCHAR, market_date DATE, anchor_type VARCHAR, anchor_date DATE, confirmation_date DATE,
            anchor_price DOUBLE, avwap DOUBLE, derivation VARCHAR, source_dates_json VARCHAR,
            price_basis VARCHAR, analysis_version VARCHAR, ruleset_version VARCHAR, created_at TIMESTAMPTZ,
            PRIMARY KEY (ticker, market_date, anchor_type, anchor_date, analysis_version, ruleset_version)
        );
        CREATE TABLE IF NOT EXISTS location_zones (
            ticker VARCHAR, market_date DATE, zone_type VARCHAR, rank INTEGER, zone_low DOUBLE, zone_high DOUBLE,
            level_types_json VARCHAR, derivations_json VARCHAR, strength_class VARCHAR, source_dates_json VARCHAR,
            analysis_version VARCHAR, ruleset_version VARCHAR, created_at TIMESTAMPTZ,
            PRIMARY KEY (ticker, market_date, zone_type, rank, analysis_version, ruleset_version)
        );
        CREATE TABLE IF NOT EXISTS location_state_daily (
            ticker VARCHAR, market_date DATE, state VARCHAR, close DOUBLE, support_zone_low DOUBLE,
            support_zone_high DOUBLE, resistance_zone_low DOUBLE, resistance_zone_high DOUBLE,
            distance_support_pct DOUBLE, distance_resistance_pct DOUBLE, observations_json VARCHAR,
            missing_inputs_json VARCHAR, source_dates_json VARCHAR, analysis_version VARCHAR,
            ruleset_version VARCHAR, created_at TIMESTAMPTZ,
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
