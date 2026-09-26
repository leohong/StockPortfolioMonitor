# Taiwan Stock Portfolio Market Structure Monitor
## V3 Migration Plan — Market Structure & Regime Decision System

> **Purpose:** Upgrade the completed V2/P1–P9 dashboard in place. Do not rebuild the product and do not discard working P1–P9 capabilities.
>
> V3 changes the analytical architecture from a seven-factor technical monitor into a hierarchical, regime-aware, auditable decision-support system.
>
> **Core principle:** preserve raw data, snapshots, provenance, no-look-ahead behavior, exports, and working UI; add new analytical layers through versioned schemas, parallel computation, regression tests, and staged cutover.
>
> This remains a research/monitoring system. It must not fabricate data, promise outcomes, or reduce the analysis to a black-box BUY/SELL score.

---

# 0. Codex Operating Instructions

Codex must treat the existing repository as a **completed V2 implementation through Phase 9**.

Before changing code:

1. Read this entire document.
2. Read the current repository structure, README, migrations, schema, tests, pages, services, providers, and analysis modules.
3. Run the current full test suite and record the baseline.
4. Start the existing application and verify the major P1–P9 pages/functions.
5. Inspect the actual implemented schema instead of assuming it exactly matches the old plan.
6. Create an implementation-gap report mapping current code to this V3 plan.
7. Do **not** delete working V2 behavior merely because V3 replaces its interpretation.
8. Use additive database migrations wherever possible.
9. Preserve old daily snapshots as historical V2 artifacts.
10. New V3 snapshots must be explicitly versioned.
11. Every historical calculation must remain point-in-time safe.
12. Implement one V3 phase at a time and run regression tests after every phase.
13. Do not silently change indicator definitions, units, source priority, or corporate-action handling.
14. If the repository differs from the expected architecture, adapt this plan to the repository rather than rebuilding it.
15. Never use future bars, future fundamentals, future index constituents, or future-confirmed pivots in historical state reconstruction.

---

# 1. Migration Objective

V2 currently provides a strong foundation:

- validated OHLCV;
- MA / RSI / volume indicators;
- institutional flows;
- margin data;
- HH / HL / LH / LL structure;
- support / resistance;
- seven-factor evidence;
- Market Stage;
- daily snapshots;
- change detection;
- Portfolio Radar;
- Timeline / Compare / Data Quality;
- CSV / PNG / PDF-style export infrastructure through P9.

V3 must preserve those capabilities and add the following missing analytical dimensions:

```text
0. Market / Sector Regime
1. Price Structure
2. Trend Quality
3. Momentum State
4. Relative Strength
5. Participation / Volume
6. Capital Flow
7. Positioning / Crowding
8. Volatility Regime
9. Location / Confluence
10. Fundamental / Event Context
        ↓
Market State
        ↓
Change Detection
        ↓
Significance Engine
        ↓
Scenario Engine
```

The most important architectural change is:

```text
V2:
seven factors → Market Stage

V3:
Market Regime
    ↓
Structure
    ↓
Trend / Momentum
    ↓
Relative Strength / Participation / Flow
    ↓
Positioning / Volatility / Location
    ↓
Market State
    ↓
Significant Changes
    ↓
Conditional Scenarios
```

V3 is therefore **hierarchical**, not a flat indicator vote.

---

# 2. Non-Negotiable Design Principles

## 2.1 Evidence before interpretation

Always preserve:

```text
Raw Data
↓
Validated Data
↓
Deterministic Features
↓
Point-in-Time Evidence
↓
Rule Engine
↓
State
↓
Scenario
↓
Optional Natural-Language Explanation
```

LLM output must never be the source of a state, indicator, support level, pivot, regime, or scenario condition.

## 2.2 No global stock score

Do not create:

```text
Technical Score = 82
Strong Buy
5 stars
90% chance of rising
```

Use an **Evidence Vector** instead.

Example:

```text
REGIME          RISK_ON_TREND
STRUCTURE       BULLISH
TREND           HEALTHY
MOMENTUM        COOLING
REL_STRENGTH    IMPROVING
PARTICIPATION   NORMAL
FLOW            POSITIVE
POSITIONING     CROWDED
VOLATILITY      NORMAL
LOCATION        NEAR_SUPPORT
```

## 2.3 State is not a prediction

State describes currently observed evidence.

Scenario describes what evidence would strengthen, weaken, or invalidate the current interpretation.

## 2.4 Point-in-time correctness

Every feature that can suffer look-ahead must retain availability/confirmation metadata.

At minimum:

```text
observation_date
available_date
confirmation_date   # where applicable
calculation_version
source
```

Historical review asks:

> What could the system actually know on that date?

## 2.5 Existing user cost remains separate

Cost basis may appear in Portfolio and Stock Detail but must not influence:

- support;
- resistance;
- AVWAP;
- structure;
- regime;
- trend;
- scenario thresholds.

---

# 3. Preserve, Refactor, Replace, Add

## 3.1 PRESERVE

Keep these P1–P9 capabilities unless regression tests prove a defect:

- provider abstraction;
- official-source priority;
- raw/normalized market data;
- DuckDB;
- data validation;
- OHLCV chart;
- institutional data;
- margin data;
- pivot confirmation model;
- support/resistance derivation;
- snapshot history;
- change events;
- Portfolio Radar;
- Timeline;
- Compare;
- Data Quality;
- export pipeline;
- logging;
- current test fixtures.

## 3.2 REFACTOR

Refactor these concepts without deleting their historical records:

```text
V2 market_stage
→ V3 market_state

V2 seven-factor evidence
→ V3 multidimensional evidence vector

V2 volume
→ participation

V2 margin
→ positioning / crowding

V2 support/resistance
→ location / confluence
```

## 3.3 ADD

Add:

```text
benchmark data
sector / industry mapping
market breadth
regime engine
trend-quality engine
relative-strength engine
positioning engine
volatility engine
AVWAP / location engine
significance engine
scenario engine
analysis-version registry
backtest / walk-forward evaluation
```

## 3.4 DEPRECATE, DO NOT IMMEDIATELY DELETE

Retain V2 fields/tables during migration:

```text
market_stage_daily
evidence_daily
old stage labels
old snapshot columns
```

Mark them:

```text
analysis_version = "v2"
deprecated = true
```

Only remove after V3 has passed a defined observation period and migration verification.

---

# 4. Target V3 Repository Structure

Adapt names to the actual repository.

```text
src/
├── analysis/
│   ├── structure/
│   │   ├── pivots.py
│   │   ├── market_structure.py
│   │   └── support_resistance.py
│   ├── regime/
│   │   ├── market_regime.py
│   │   ├── breadth.py
│   │   └── sector_regime.py
│   ├── trend/
│   │   ├── trend_quality.py
│   │   └── moving_average_features.py
│   ├── momentum/
│   │   ├── rsi.py
│   │   ├── roc.py
│   │   └── divergence.py
│   ├── relative_strength/
│   │   ├── benchmark.py
│   │   └── relative_strength.py
│   ├── participation/
│   │   └── volume_participation.py
│   ├── flow/
│   │   └── institutional_flow.py
│   ├── positioning/
│   │   ├── margin.py
│   │   ├── short.py
│   │   └── crowding.py
│   ├── volatility/
│   │   ├── atr.py
│   │   ├── historical_volatility.py
│   │   └── volatility_regime.py
│   ├── location/
│   │   ├── levels.py
│   │   ├── anchored_vwap.py
│   │   └── confluence.py
│   ├── fundamentals/
│   │   └── context.py
│   ├── evidence/
│   │   ├── models.py
│   │   └── evidence_engine.py
│   ├── state/
│   │   ├── market_state.py
│   │   └── transition.py
│   ├── significance/
│   │   └── significance_engine.py
│   └── scenarios/
│       └── scenario_engine.py
│
├── evaluation/
│   ├── point_in_time.py
│   ├── walk_forward.py
│   ├── event_study.py
│   ├── robustness.py
│   └── metrics.py
│
├── snapshots/
│   ├── v2_adapter.py
│   ├── v3_snapshot.py
│   └── migration.py
│
└── services/
    ├── regime_service.py
    ├── analysis_service_v3.py
    └── scenario_service.py
```

Do not create empty architecture for appearance. Add modules only when their phase is implemented.

---

# 5. Analysis Versioning

Create a first-class version registry.

Minimum:

```text
analysis_version
ruleset_version
schema_version
created_at
git_commit
config_hash
```

Every V3 snapshot must record:

```text
analysis_version = "v3"
ruleset_version
```

Never overwrite a V2 snapshot with V3 output.

The same market date may legitimately have:

```text
ticker | market_date | analysis_version
3702   | 2026-09-24  | v2
3702   | 2026-09-24  | v3
```

This is required for auditability.

---

# 6. New Data Requirements

## 6.1 Benchmark data

Minimum:

```text
TAIEX
OTC index where relevant
```

Store daily OHLCV with source metadata.

## 6.2 Sector / industry mapping

For each stock:

```text
ticker
sector
industry
classification_source
effective_from
effective_to
```

Never use today's classification blindly in old historical snapshots if classification changed.

## 6.3 Breadth data

Where reliable data is available, support:

```text
advancing_count
declining_count
unchanged_count
new_high_count
new_low_count
pct_above_ma20
pct_above_ma60
```

Do not fabricate unavailable historical breadth.

Regime must degrade gracefully if breadth is unavailable.

## 6.4 Corporate events

Reuse V2 corporate-action handling and extend context when available:

```text
earnings/reported financial date
monthly revenue release
ex-dividend
capital reduction
split
rights issue
material company announcement
```

Store both event date and information-available date.

---

# 7. Regime Engine

Regime is calculated before individual-stock state.

Initial allowed market regimes:

```text
RISK_ON_TREND
RISK_ON_EXTENDED
RANGE_ROTATION
RISK_OFF
TRANSITION
INSUFFICIENT_DATA
```

Inputs may include:

```text
benchmark price vs MA20/MA60/MA120
MA20 slope
MA60 slope
benchmark structure
benchmark RSI
benchmark ATR%
breadth
sector participation
```

Do not require every input.

Return structured evidence:

```json
{
  "regime": "RISK_ON_TREND",
  "confidence_class": "CONFIRMED",
  "evidence_for": [],
  "evidence_against": [],
  "missing_inputs": [],
  "as_of_date": "YYYY-MM-DD"
}
```

`confidence_class` is evidence completeness, not probability.

Allowed:

```text
CONFIRMED
MIXED
TENTATIVE
INSUFFICIENT
```

Do not output numerical probability unless a separately validated statistical model is later introduced.

---

# 8. Sector Regime

Calculate the same directional context for the stock's sector/industry when reliable benchmark data exists.

Output:

```text
MARKET_REGIME
SECTOR_REGIME
REGIME_ALIGNMENT
```

Alignment:

```text
ALIGNED_POSITIVE
ALIGNED_NEGATIVE
STOCK_AGAINST_MARKET
MIXED
UNKNOWN
```

This is descriptive, not a recommendation.

---

# 9. Structure Engine V3

Preserve the existing pivot and no-look-ahead logic.

Required structure evidence:

```text
latest confirmed swing high
latest confirmed swing low
previous comparable swing
HH / HL / LH / LL
break of structure
failed break
reclaim
pivot_date
confirmation_date
```

New optional states:

```text
BULLISH_STRUCTURE
BEARISH_STRUCTURE
RANGE_STRUCTURE
POSSIBLE_REVERSAL
UNCONFIRMED
```

Do not let MA or RSI override confirmed price structure.

Priority:

```text
Structure > Trend > Momentum
```

---

# 10. Trend Quality Engine

Do not treat MA ordering alone as the trend.

Calculate:

```text
MA5
MA20
MA60
MA120

MA20 slope
MA60 slope
MA120 slope

price distance from MA20
price distance from MA60

MA20/MA60 separation
trend persistence
```

Initial states:

```text
TREND_EMERGING
TREND_HEALTHY
TREND_EXTENDED
TREND_DECELERATING
TREND_BROKEN
RANGE
INSUFFICIENT_DATA
```

Trend rules must be configurable and regression tested.

---

# 11. Momentum Engine

Keep RSI14.

Add only indicators with explicit analytical purpose.

V3 minimum:

```text
RSI14
RSI slope/change
RSI 30/50/70/80 crosses
confirmed RSI divergence
ROC20 or equivalent medium-horizon momentum
```

Momentum states:

```text
ACCELERATING
POSITIVE
COOLING
NEUTRAL
WEAKENING
NEGATIVE
RESET
INSUFFICIENT_DATA
```

Important rule:

```text
RSI > 70 != sell
RSI < 30 != buy
```

A bullish structure with RSI cooling toward 50 may be classified as `RESET`, not automatically bearish.

---

# 12. Relative Strength Engine

This is a new core V3 feature.

Calculate stock performance relative to:

```text
market benchmark
sector benchmark, if available
```

Minimum windows:

```text
20D
60D
120D
```

Example:

```text
RS_market_20 =
stock_return_20d - benchmark_return_20d
```

Also maintain a normalized relative-strength line:

```text
stock_close / benchmark_close
```

Optional normalization:

```text
RS line indexed to 100 at window start
```

States:

```text
LEADING
IMPROVING
NEUTRAL
WEAKENING
LAGGING
INSUFFICIENT_DATA
```

Detect useful divergences such as:

```text
stock price consolidating
while RS line makes new high
```

but store the underlying observations rather than using narrative-only labels.

---

# 13. Participation Engine

Rename the conceptual role of V2 Volume to Participation.

Use:

```text
volume
volume_ma5
volume_ma20
volume_ratio_20
turnover
close location within daily range
breakout participation
breakdown participation
```

Example evidence:

```text
Resistance break
Volume Ratio = 1.8x
Close Location Value high
→ breakout participation strengthened
```

Do not call high volume "distribution" by itself.

States:

```text
STRONG_CONFIRMATION
CONFIRMING
NORMAL
WEAK_CONFIRMATION
CONTRADICTORY
ABNORMAL
INSUFFICIENT_DATA
```

---

# 14. Capital Flow Engine

Preserve separate:

```text
Foreign
Investment Trust
Dealer
```

Keep:

```text
1D
3D
5D
10D
20D
```

Add persistence features.

Example:

```text
positive_days_10d
negative_days_10d
net_flow_10d
flow_persistence_10d
```

A simple descriptive persistence metric may be:

```text
positive_flow_days / valid_days
```

Do not interpret the metric alone; retain net magnitude and direction.

States per participant:

```text
PERSISTENT_BUYING
BUYING
NEUTRAL
SELLING
PERSISTENT_SELLING
REVERSING_POSITIVE
REVERSING_NEGATIVE
```

---

# 15. Positioning / Crowding Engine

V2 Margin becomes one component of Positioning.

Inputs:

```text
margin balance
margin change 5D/10D/20D
margin change %
short balance
short changes
price return over same window
turnover/liquidity context
```

Add descriptive leverage divergence:

```text
leverage_divergence_20d =
margin_change_pct_20d - price_return_pct_20d
```

This is not itself a signal.

Detect combinations:

```text
price ↑ + margin ↑ slowly
price ↑ + margin ↑ rapidly
price ↓ + margin ↑
price ↓ + margin ↓
```

States:

```text
HEALTHY
NORMAL
LEVERAGE_EXPANDING
CROWDED
DELEVERAGING
STRESS
INSUFFICIENT_DATA
```

Thresholds must be configurable and evaluated empirically.

---

# 16. Volatility Engine

Add:

```text
ATR14
ATR14_pct
20D realized/historical volatility
range_ratio
gap size
volatility percentile using trailing history
```

States:

```text
COMPRESSED
NORMAL
EXPANDING
HIGH
SHOCK
INSUFFICIENT_DATA
```

Volatility must modify interpretation.

Example:

A 4% move when ATR% is 1% is materially different from a 4% move when ATR% is 5%.

Do not use volatility as directional evidence by itself.

---

# 17. Location / Confluence Engine

Expand V2 support/resistance.

Sources:

```text
confirmed swing high/low
breakout/breakdown level
prior resistance/support
MA20
MA60
MA120
gap boundaries
high-volume areas where valid
Anchored VWAP
```

## 17.1 Anchored VWAP

Initial supported anchors:

```text
confirmed major swing low
confirmed major swing high
breakout date
large-volume event
gap event
```

All anchors must be deterministic and auditable.

Do not let an LLM choose anchors.

## 17.2 Confluence zones

Nearby independently derived levels may form a zone.

Example:

```text
Support Zone: 108–111

Evidence:
- previous resistance = 109
- breakout level = 110
- AVWAP = 109.6
- MA20 = 110.8
```

Return:

```text
zone_low
zone_high
level_types
derivations
strength_class
```

Avoid fake precision.

States:

```text
AT_SUPPORT
NEAR_SUPPORT
MID_RANGE
NEAR_RESISTANCE
AT_RESISTANCE
BREAKOUT_ZONE
BREAKDOWN_ZONE
NO_CLEAR_LOCATION
```

---

# 18. Fundamental / Catalyst Context

This remains contextual rather than a short-term timing vote.

After V3 core migration is stable, integrate the V2/P10-style fundamentals if available:

```text
monthly revenue
YoY
EPS
gross margin
operating margin
net margin
ROE
FCF
valuation context
```

The main question is:

```text
Is price deterioration occurring
with
or without
business deterioration?
```

Catalyst/event context must use point-in-time availability.

---

# 19. Evidence Vector V3

Replace the seven-card conceptual model with a versioned multidimensional evidence object.

Minimum dimensions:

```text
regime
sector_regime
structure
trend
momentum
relative_strength
participation
capital_flow
positioning
volatility
location
fundamental_context
```

Example:

```json
{
  "ticker": "3702",
  "market_date": "YYYY-MM-DD",
  "analysis_version": "v3",
  "dimensions": {
    "regime": {
      "state": "RISK_ON_TREND",
      "evidence_for": [],
      "evidence_against": []
    },
    "structure": {
      "state": "BULLISH_STRUCTURE",
      "evidence_for": [],
      "evidence_against": []
    }
  }
}
```

Every dimension must support:

```text
state
headline
observations
evidence_for
evidence_against
missing_data
source_dates
calculation_version
```

---

# 20. Market State Engine V3

Replace the old A–G model for new V3 snapshots.

Allowed V3 states:

```text
S0_DECLINE
S1_STABILIZATION
S2_BASE
S3_BREAKOUT
S4_TREND
S5_EXTENSION
S6_DISTRIBUTION_RISK
S7_CORRECTION
S8_STRUCTURE_FAILURE
TRANSITION
UNCLASSIFIED
```

Important:

`DISTRIBUTION_RISK` is a risk-state label, not a factual claim that an operator or institution is distributing shares.

## 20.1 Hierarchical decision order

Rules should approximately follow:

```text
1. Data quality
2. Market/sector regime
3. Price structure
4. Trend
5. Momentum
6. Relative strength
7. Participation
8. Capital flow
9. Positioning
10. Volatility
11. Location
```

Lower layers may strengthen/weaken interpretation but should not casually override broken structure.

## 20.2 State output

Return:

```text
state
previous_state
transition
primary_evidence
supporting_evidence
contradicting_evidence
invalidation_conditions
unresolved_questions
```

---

# 21. Significance Engine

V2 detects changes. V3 must answer:

> Which changes matter?

Keep raw change events, then add significance.

Initial levels:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Do not use significance as a buy/sell score.

Examples:

```text
RSI 61 → 59
→ LOW

Volume Ratio 1.0 → 1.4
→ LOW/MEDIUM depending on context

Foreign 5D positive → negative
→ MEDIUM

New confirmed Lower High
→ HIGH

Key support broken
→ HIGH

Support break
+ Volume expansion
+ persistent foreign selling
+ leverage expansion
→ CRITICAL structural-risk event
```

Significance must be rule-based and explainable.

Store:

```text
event_id
significance
context_features
reason_codes
analysis_version
```

---

# 22. Scenario Engine

This is the V3 decision-support endpoint.

Generate **conditional scenarios**, not forecasts.

Always support:

```text
POSITIVE / CONTINUATION scenario
NEUTRAL / UNRESOLVED scenario
NEGATIVE / DETERIORATION scenario
```

Each scenario contains:

```text
name
current_status
conditions
confirmation_events
invalidation_events
relevant_levels
evidence_dependencies
```

Example:

```text
Continuation scenario

Conditions:
- support zone 108–111 holds
- RSI remains/reclaims > 50
- relative strength remains improving
- price confirms resistance break

Interpretation:
Trend-continuation evidence strengthens.
```

Negative example:

```text
Deterioration scenario

Conditions:
- key support breaks
- reclaim fails
- confirmed LH forms
- Foreign 5D turns negative

Interpretation:
Structure-deterioration evidence strengthens.
```

Do not generate target prices unless a separate deterministic method is explicitly implemented and labeled.

---

# 23. Dashboard V3

Do not throw away the current UI.

Modify incrementally.

## 23.1 Portfolio Radar

Retain current table and add:

```text
Market Regime
Sector Regime
V3 State
Relative Strength
Positioning
Volatility
Significant Change?
Highest Significance
```

Default attention view:

```text
changed only
HIGH/CRITICAL only
data-quality failures
```

Do not rank holdings best-to-worst.

## 23.2 Stock Detail

Recommended order:

```text
Header
↓
Market + Sector Regime strip
↓
Current V3 Market State
↓
Scenario panel
↓
Evidence Vector cards
↓
Five-layer chart
↓
Relative Strength panel
↓
Positioning / Volatility panel
↓
Yesterday vs Today
↓
Significant Events
↓
State Timeline
↓
Data Provenance
```

## 23.3 Evidence cards

Cards become:

```text
Structure
Trend
Momentum
Relative Strength
Participation
Capital Flow
Positioning
Volatility
Location
```

Regime is displayed separately because it is higher-level context.

Fundamentals remain contextual.

## 23.4 Chart

Preserve existing synchronized five-layer chart.

Add toggles rather than permanently crowding it:

```text
AVWAP
support zones
resistance zones
V3 state regions
significant events
relative-strength line
ATR/volatility events
```

Relative strength may be a separate panel if readability is better.

---

# 24. Yesterday vs Today V3

Retain V2 functionality and extend:

| Dimension | Previous | Current | Changed? | Significance |
|---|---|---|---|---|
| Market Regime | | | | |
| Sector Regime | | | | |
| V3 State | | | | |
| Structure | | | | |
| Trend | | | | |
| Momentum | | | | |
| Relative Strength | | | | |
| Participation | | | | |
| Flow | | | | |
| Positioning | | | | |
| Volatility | | | | |
| Location | | | | |

Then:

```text
New High-Significance Evidence
Resolved Risks
New Contradictions
Scenario Conditions Triggered
Scenario Conditions Invalidated
```

---

# 25. Database Migration

Codex must inspect the actual existing schema first.

Prefer additive migrations.

Recommended new tables:

```text
analysis_versions
benchmark_daily
sector_classification
sector_benchmark_daily
market_breadth_daily

regime_daily
relative_strength_daily
trend_quality_daily
momentum_state_daily
participation_daily
positioning_daily
volatility_daily
anchored_vwap_daily
location_zones

evidence_v3_daily
market_state_v3_daily
scenario_daily
event_significance
snapshot_v3_daily
```

Use:

```text
ticker + market_date + analysis_version
```

where appropriate.

Never rewrite V2 snapshot history in place.

Migration must be reversible where practical.

---

# 26. Snapshot V3

Create one complete point-in-time V3 snapshot per stock/date/version.

Suggested fields:

```text
ticker
market_date
analysis_version
ruleset_version

close

market_regime
sector_regime
market_state

structure_state
trend_state
momentum_state
relative_strength_state
participation_state
flow_state
positioning_state
volatility_state
location_state

rsi14
ma20
ma60
ma120
atr14_pct

rs_market_20d
rs_market_60d
rs_sector_20d

volume_ratio_20

foreign_5d
foreign_20d
trust_5d
trust_20d

margin_change_pct_20d
leverage_divergence_20d

support_zone_low
support_zone_high
resistance_zone_low
resistance_zone_high

highest_event_significance
data_quality_status

created_at
```

Large evidence/scenario structures may be normalized into related tables rather than stuffed into one row.

---

# 27. Backward Compatibility

During migration the app must support:

```text
V2 historical view
V3 historical view
```

or provide an explicit compatibility adapter.

Do not visually imply that V2 and V3 state labels are equivalent.

A migration mapping may be displayed for explanation only, e.g.:

```text
V2 Uptrend
roughly corresponds to possible V3 S4 Trend
```

but do not mechanically convert old snapshots without recomputation.

---

# 28. Research / Evaluation Framework

V3 must not be accepted merely because charts look reasonable.

Create an evaluation layer.

## 28.1 Point-in-time replay

For historical date D:

```text
load only data available by D
calculate features
calculate regime
calculate evidence
calculate state
calculate scenarios
```

Compare to persisted snapshot.

## 28.2 Walk-forward testing

Use chronological splits.

Never random-shuffle time-series observations for strategy validation.

Suggested:

```text
Train/configuration period
→ Validation period
→ Forward test period
→ Roll forward
```

The rule engine is primarily deterministic, but threshold calibration must still be tested out-of-sample.

## 28.3 Event studies

Evaluate descriptive events such as:

```text
confirmed breakout
support break
new HL
new LH
RS improvement
foreign-flow reversal
margin acceleration
volatility shock
```

Measure subsequent distributions over:

```text
5D
10D
20D
60D
```

Report distributions, hit rates where well-defined, median/mean returns, drawdowns, and sample counts.

Do not turn noisy historical association into certainty.

## 28.4 Robustness

Test nearby parameter values.

Example:

```text
RSI = 14
also inspect 12 / 16

MA20
inspect nearby windows where appropriate

pivot sensitivity
test multiple valid settings
```

If results collapse under tiny parameter changes, flag instability.

## 28.5 Data-snooping protection

Maintain a registry of experiments:

```text
experiment_id
hypothesis
parameters
dataset
start_date
end_date
metrics
result
created_at
```

Do not repeatedly optimize on the same test set.

---

# 29. Test Requirements

Preserve all existing P1–P9 tests.

Add:

```text
test_analysis_versioning.py
test_regime.py
test_sector_regime.py
test_trend_quality.py
test_relative_strength.py
test_participation.py
test_flow_persistence.py
test_positioning.py
test_volatility.py
test_anchored_vwap.py
test_location_confluence.py
test_evidence_v3.py
test_market_state_v3.py
test_significance.py
test_scenarios.py
test_point_in_time_replay.py
test_v2_v3_coexistence.py
test_migrations.py
```

Required invariants:

```text
future data never changes an already persisted historical V3 snapshot
unconfirmed pivots cannot enter historical state
benchmark dates align correctly
missing benchmark does not fabricate RS
missing breadth does not fabricate regime evidence
cost basis never changes technical levels
V2 snapshots remain unchanged
```

---

# 30. Migration Phases for a Repository That Already Completed P1–P9

Do **not** restart at Phase 0.

Use migration phases M0–M9.

---

# M0 — Repository Audit and Baseline Freeze

Deliver:

```text
V3_MIGRATION_AUDIT.md
baseline test report
current schema inventory
current page inventory
current analysis dependency graph
V2 compatibility risks
```

Tasks:

1. Run all tests.
2. Record current commit.
3. Inspect actual DB schema.
4. Inspect data providers and source metadata.
5. Verify P1–P9 functionality.
6. Identify hard-coded stage/evidence assumptions.
7. Identify schema changes needed.
8. Do not modify analytical behavior yet.

Acceptance:

```text
baseline is reproducible
all known failures documented
migration plan references actual code
```

---

# M1 — Versioning + Schema Foundation

Implement:

```text
analysis_versions
ruleset_version
V3 additive migrations
V3 model objects
V2/V3 coexistence
```

No UI redesign yet.

Acceptance:

```text
existing V2 app still works
old snapshots unchanged
new schema initializes
migration tests pass
rollback documented
```

---

# M2 — Benchmark + Regime

Implement:

```text
TAIEX/benchmark provider
sector mapping
sector benchmark where feasible
breadth when reliable
market regime
sector regime
```

UI:

small Regime strip only.

Acceptance:

```text
real benchmark data
source/date metadata
point-in-time tests
missing breadth handled explicitly
no effect on V2 state yet
```

---

# M3 — Trend + Momentum V3 + Relative Strength

Implement:

```text
trend quality
RSI state refinement
ROC
relative strength vs market
relative strength vs sector
```

Do not replace V2 Market Stage yet.

Acceptance:

```text
deterministic outputs
20D/60D/120D RS verified manually
benchmark alignment tests
corporate-action handling verified
```

---

# M4 — Participation + Flow Persistence + Positioning

Implement:

```text
participation engine
flow persistence
positioning/crowding
leverage divergence
```

Reuse existing institutional and margin data.

Acceptance:

```text
no duplicate data retrieval architecture
old institutional/margin pages remain valid
new states trace to raw observations
thresholds configurable
```

---

# M5 — Volatility + Location / AVWAP

Implement:

```text
ATR14
ATR%
historical volatility
volatility regime
deterministic AVWAP anchors
support/resistance confluence
location zones
```

Acceptance:

```text
AVWAP anchors auditable
no future pivot anchors
zones include derivation
no fake precision
```

---

# M6 — Evidence Vector + Market State V3

Implement:

```text
evidence_v3
market_state_v3
transition rules
contradicting evidence
invalidation conditions
```

Run V2 and V3 in parallel.

Acceptance:

```text
every state explainable
no black-box score
state does not depend on LLM
historical replay passes
V2 still available
```

---

# M7 — Significance + Scenario Engine

Implement:

```text
event significance
scenario generation
scenario condition tracking
scenario invalidation
```

Acceptance:

```text
scenarios are conditional
no forecasts disguised as scenarios
no unsupported target prices
all conditions reference structured evidence
```

---

# M8 — UI Cutover

Upgrade:

```text
Portfolio Radar
Stock Detail
Yesterday vs Today
Timeline
Compare
Exports
```

Default to V3 for new analysis, while retaining V2 historical access during transition.

Acceptance:

```text
user can inspect why state changed
user can inspect evidence against current state
HIGH/CRITICAL filter works
scenario conditions visible
charts remain synchronized
existing exports do not regress
```

---

# M9 — Validation, Walk-Forward, Documentation, V2 Deprecation Decision

Implement:

```text
point-in-time replay suite
event-study reports
walk-forward evaluation
parameter robustness
performance tests
migration documentation
```

Do not delete V2 automatically.

Create:

```text
V3_VALIDATION_REPORT.md
V3_MIGRATION_REPORT.md
V2_DEPRECATION_RECOMMENDATION.md
```

Only recommend V2 removal if:

```text
V3 has stable snapshots
regression suite passes
historical replay passes
UI/export parity is achieved
user has accepted V3 workflow
```

---

# 31. Codex Execution Rule

Codex must implement **one migration phase per task**.

For every phase:

1. State files to change.
2. State DB migration.
3. Implement.
4. Add tests.
5. Run focused tests.
6. Run full regression suite.
7. Start app if UI changed.
8. Report failures.
9. Update migration notes.
10. Stop.

Do not proceed automatically to the next migration phase unless explicitly requested.

---

# 32. First Codex Task

Use this exact starting task:

```text
Read V3_MIGRATION_PLAN.md completely.

The existing project has already completed the previous P1–P9 implementation.
Do NOT rebuild the application.

Perform M0 only: Repository Audit and Baseline Freeze.

Tasks:
1. Inspect the actual repository structure.
2. Read README, configuration, schema/migrations, providers, indicators,
   analysis modules, snapshot/change-detection code, services, pages,
   export code, and tests.
3. Run the complete current test suite.
4. Record current test results and failures.
5. Inspect the actual DuckDB schema/migrations.
6. Map implemented P1–P9 functionality to V3 requirements.
7. Identify all code and schema locations coupled to:
   - seven-factor evidence
   - old Market Stage
   - margin interpretation
   - volume interpretation
   - support/resistance
   - snapshots
   - change detection
   - exports
8. Identify look-ahead risks.
9. Identify backward-compatibility risks.
10. Produce V3_MIGRATION_AUDIT.md.

Do not implement V3 features yet.
Do not change analytical behavior.
Do not delete or rename existing tables.
Do not modify historical snapshots.

At the end report:
- baseline tests
- current architecture
- migration risks
- recommended M1 file changes
- recommended M1 DB migrations
- blockers, if any
```

---

# 33. Second Codex Task

After M0 review:

```text
Implement M1 only: Versioning + Schema Foundation.

Use V3_MIGRATION_AUDIT.md as the source of truth for actual repository paths.

Requirements:
- additive migrations only unless explicitly justified;
- preserve all V2 snapshots;
- add analysis/ruleset versioning;
- create V3 domain models;
- make V2 and V3 coexist;
- add migration/versioning tests;
- run full regression suite.

Do not implement Regime yet.
```

---

# 34. Third Codex Task

After M1 passes:

```text
Implement M2 only: Benchmark + Market/Sector Regime.

Requirements:
- use real sourced benchmark data;
- retain provenance;
- point-in-time safe calculations;
- sector classification must support effective dates where possible;
- breadth is optional when reliable data is unavailable;
- missing breadth must remain missing;
- expose regime evidence;
- add a minimal non-disruptive Regime UI strip;
- do not replace V2 Market Stage.

Run full regression tests.
```

---

# 35. Fourth Codex Task

After M2 passes:

```text
Implement M3 only: Trend Quality + Momentum V3 + Relative Strength.

Requirements:
- preserve existing MA/RSI calculations unless a verified defect exists;
- add slopes/separation/persistence;
- add momentum states;
- add market and sector relative strength;
- verify 20D/60D/120D calculations manually on regression tickers;
- no V3 Market State yet.

Run full regression tests.
```

---

# 36. Fifth Codex Task

After M3 passes:

```text
Implement M4 only: Participation + Flow Persistence + Positioning.

Reuse the existing V2 volume, institutional, margin and short datasets.

Do not build duplicate providers if existing normalized data is valid.

Add:
- participation states;
- institutional flow persistence;
- positioning/crowding;
- leverage divergence;
- explainable evidence objects.

Run full regression tests.
```

---

# 37. Sixth Codex Task

After M4 passes:

```text
Implement M5 only: Volatility + Location/AVWAP.

Add:
- ATR14 / ATR%;
- historical volatility;
- volatility states;
- deterministic AVWAP anchors;
- support/resistance confluence zones;
- location states.

No LLM-selected anchors.
No future-confirmed pivots.
Run point-in-time tests and full regression tests.
```

---

# 38. Seventh Codex Task

After M5 passes:

```text
Implement M6 only: V3 Evidence Vector + V3 Market State.

Requirements:
- use hierarchical evidence;
- no total score;
- include supporting and contradicting evidence;
- include invalidation conditions;
- persist V3 snapshots separately;
- run V2 and V3 in parallel;
- implement point-in-time replay.

Do not remove V2.
```

---

# 39. Eighth Codex Task

After M6 passes:

```text
Implement M7 only: Significance + Scenario Engine.

Requirements:
- classify event significance LOW/MEDIUM/HIGH/CRITICAL;
- significance is attention priority, not trade advice;
- create positive/neutral/negative conditional scenarios;
- every condition references structured data;
- scenario invalidation must be explicit;
- no probabilistic forecast;
- no fabricated target prices.

Run full regression tests.
```

---

# 40. Ninth Codex Task

After M7 passes:

```text
Implement M8 only: V3 UI Cutover.

Upgrade existing pages rather than rewriting them.

Priority:
1. Portfolio Radar
2. Stock Detail
3. Yesterday vs Today
4. Timeline
5. Compare
6. Export

Add V3 evidence, regimes, scenarios and significance while preserving
existing chart/data-quality functionality.

Keep V2 historical access during transition.
Run UI smoke tests and full regression tests.
```

---

# 41. Tenth Codex Task

After M8 passes:

```text
Implement M9 only: Validation and Migration Completion.

Add:
- historical point-in-time replay;
- event studies;
- chronological walk-forward evaluation;
- parameter robustness checks;
- performance benchmarks;
- V3 validation report;
- V3 migration report;
- V2 deprecation recommendation.

Do not delete V2 automatically.
```

---

# 42. Definition of Done for V3

V3 is practically complete when:

```text
[ ] P1–P9 functionality has not regressed
[ ] V2 history remains auditable
[ ] V3 snapshots are versioned
[ ] Market Regime works
[ ] Sector context works where data exists
[ ] Trend Quality works
[ ] Relative Strength works
[ ] Participation works
[ ] Flow Persistence works
[ ] Positioning/Crowding works
[ ] Volatility works
[ ] AVWAP/Location works
[ ] Evidence Vector works
[ ] V3 Market State works
[ ] Significance works
[ ] Scenario Engine works
[ ] Yesterday vs Today supports V3
[ ] Portfolio Radar supports V3
[ ] Timeline supports V3
[ ] exports reproduce the same V3 snapshot
[ ] historical replay has no look-ahead leakage
[ ] missing data stays missing
[ ] full regression suite passes
[ ] walk-forward/evaluation reports exist
```

---

# 43. Final Product Questions

The finished dashboard should answer, in this order:

```text
1. What market regime are we in?
2. Is this stock aligned with or diverging from its market/sector?
3. What is the confirmed price structure?
4. Is the trend healthy, extended, decelerating, or broken?
5. Is momentum confirming, cooling, resetting, or deteriorating?
6. Is relative strength improving or weakening?
7. Is participation confirming the move?
8. Are institutional flows persistent or reversing?
9. Is leverage/positioning becoming crowded?
10. Is volatility normal or abnormal?
11. Where is price relative to meaningful support/resistance/AVWAP?
12. What changed since the previous valid snapshot?
13. Which changes actually matter?
14. What evidence contradicts the current interpretation?
15. What would invalidate the current state?
16. What conditions define continuation, unresolved, and deterioration scenarios?
```

The system's goal remains:

> **Build a repeatable, auditable, point-in-time-correct process for understanding market structure, changes, and risk — not a black-box predictor.**
