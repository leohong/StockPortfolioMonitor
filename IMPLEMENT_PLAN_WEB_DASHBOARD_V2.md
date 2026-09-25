# Taiwan Stock Portfolio Market Structure Monitor
## Web Dashboard V2 — Implementation Plan

> Purpose: Build a local-first Taiwan-stock portfolio monitoring dashboard that collects real market data, validates it, applies a consistent 7-factor analysis framework, detects market-stage changes, and explains the evidence behind each conclusion.
>
> This is **not** an AI stock-price predictor and **not** an automated trading bot.

---

# 1. Product Goal

Replace the previous static-chart-first workflow with an **interactive Web Dashboard**.

Primary workflow:

```text
Real Market Data
      ↓
Data Validation
      ↓
DuckDB Storage
      ↓
Indicators
      ↓
Price Structure HH/HL/LH/LL
      ↓
Institutional + Margin Analysis
      ↓
7-Factor Evidence Engine
      ↓
Market Stage Engine
      ↓
Daily Snapshot
      ↓
Change Detection
      ↓
Web Dashboard
      ↓
Optional PNG / PDF / CSV Export
```

The dashboard should answer:

1. Which holdings changed today?
2. Which holdings need attention?
3. What market stage is each holding in?
4. Why did the system classify it that way?
5. Which evidence is improving?
6. Which evidence is deteriorating?
7. Which price level would invalidate the current interpretation?
8. How has the stock's state changed over time?

---

# 2. Core Analysis Framework

Always preserve this hierarchy:

> **Price = structure → RSI = momentum → MA = trend → Volume = participation → Institutional = capital flow → Margin = leverage risk → Support/Resistance = location → Fundamentals = business context**

The seven primary factors are:

| # | Factor | Purpose |
|---|---|---|
| 1 | Price Structure | Direction: HH / HL / LH / LL |
| 2 | RSI(14) | Momentum / overextension / divergence |
| 3 | MA5 / MA20 / MA60 | Trend |
| 4 | Volume | Participation and confirmation |
| 5 | Foreign / Trust / Dealer | Institutional flows |
| 6 | Margin | Leverage and crowding risk |
| 7 | Support / Resistance | Location and invalidation levels |

Fundamentals are a contextual layer rather than a technical timing signal.

Rules:

- Never make a conclusion from one indicator alone.
- Never claim a top or bottom with certainty.
- Never equate RSI > 70 with “sell”.
- Never equate RSI < 30 with “buy”.
- Never equate high volume with “distribution”.
- Never equate margin growth with “everyone is profitable”.
- Never claim “主力洗盤 / 出貨 / 吸籌 / 散戶踩踏” as fact without evidence.
- Separate raw data, calculated values, deterministic interpretation, and optional AI explanation.
- Missing data remains missing; never fabricate values.

---

# 3. Recommended Stack

## Application

- Python 3.12+
- Streamlit
- Plotly

## Analytics

- Pandas or Polars
- NumPy
- Pydantic

## Database

- DuckDB

## Data Retrieval

- httpx
- tenacity

## Testing

- pytest

Do not start V1 with React + FastAPI + PostgreSQL.

The first goal is a reliable personal research dashboard that Codex can implement and maintain efficiently.

---

# 4. Repository Structure

```text
stock-dashboard/
├── README.md
├── IMPLEMENT_PLAN.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── app.py
│
├── pages/
│   ├── 1_portfolio.py
│   ├── 2_stock_detail.py
│   ├── 3_compare.py
│   ├── 4_timeline.py
│   └── 5_data_quality.py
│
├── config/
│   ├── settings.yaml
│   ├── sources.yaml
│   └── holdings.yaml
│
├── src/
│   ├── models.py
│   ├── config.py
│   │
│   ├── data/
│   │   ├── providers/
│   │   │   ├── base.py
│   │   │   ├── twse.py
│   │   │   ├── tpex.py
│   │   │   ├── mops.py
│   │   │   └── fallback.py
│   │   ├── collector.py
│   │   ├── normalizer.py
│   │   ├── validator.py
│   │   └── cache.py
│   │
│   ├── database/
│   │   ├── db.py
│   │   ├── schema.py
│   │   └── migrations.py
│   │
│   ├── indicators/
│   │   ├── moving_average.py
│   │   ├── rsi.py
│   │   ├── volume.py
│   │   └── divergence.py
│   │
│   ├── analysis/
│   │   ├── price_structure.py
│   │   ├── institutional.py
│   │   ├── margin.py
│   │   ├── support_resistance.py
│   │   ├── fundamentals.py
│   │   ├── evidence.py
│   │   ├── market_stage.py
│   │   └── change_detection.py
│   │
│   ├── charts/
│   │   ├── stock_chart.py
│   │   ├── portfolio_chart.py
│   │   └── export_chart.py
│   │
│   ├── reports/
│   │   ├── markdown_report.py
│   │   ├── png_export.py
│   │   └── pdf_export.py
│   │
│   └── services/
│       ├── stock_service.py
│       ├── portfolio_service.py
│       └── snapshot_service.py
│
├── data/
│   ├── stocks.duckdb
│   ├── cache/
│   └── exports/
│
└── tests/
    ├── test_validator.py
    ├── test_indicators.py
    ├── test_price_structure.py
    ├── test_market_stage.py
    ├── test_change_detection.py
    └── fixtures/
```

---

# 5. Data Source Policy

Priority:

1. TWSE official data
2. TPEx official data
3. MOPS
4. Company IR
5. Reliable secondary source only as fallback

Every dataset must retain:

```text
source
source_type
is_official
retrieved_at
market_date
```

If sources disagree:

- preserve the discrepancy;
- prefer official data;
- generate a Data Quality warning;
- never silently select the value that best fits the analysis.

---

# 6. Required Data

## 6.1 OHLCV

Store at least 250 trading days when available:

```text
ticker
date
open
high
low
close
volume
turnover
source
```

## 6.2 Institutional Trading

Daily:

```text
foreign_net
investment_trust_net
dealer_net
institutional_total_net
```

Calculate:

```text
3D
5D
10D
20D
```

for each participant independently.

## 6.3 Margin / Short

Daily:

```text
margin_buy
margin_sell
margin_cash_repayment
margin_balance

short_sell
short_cover
short_balance
```

Calculate:

```text
margin_change_1d
margin_change_5d
margin_change_10d
margin_change_20d
margin_change_pct_20d
```

## 6.4 Fundamentals

Minimum:

```text
monthly_revenue
monthly_revenue_yoy
quarterly_eps
cumulative_eps
gross_margin
operating_margin
net_margin
```

When available:

```text
ROE
free_cash_flow
dividend
dividend_yield
PE
PB
```

Purpose:

Distinguish **price correction** from **business deterioration**.

---

# 7. Data Validation Gate

No normal analysis may run until validation completes.

Validate:

1. `low <= open <= high`
2. `low <= close <= high`
3. duplicate dates
4. date ordering
5. missing sessions
6. impossible volume
7. volume units
8. institutional units
9. margin units
10. stale data
11. ex-dividend events
12. stock splits
13. capital reductions
14. capital increases
15. suspicious discontinuities
16. source conflicts

Result:

```text
PASS
PASS_WITH_WARNINGS
FAIL
```

`FAIL` must prevent normal Market Stage classification.

---

# 8. Indicator Engine

Calculate:

```text
MA5
MA10
MA20
MA60
MA120

RSI14

Volume_MA5
Volume_MA20
Volume_Ratio_20

Return_20D
Return_60D

Distance_MA20_Pct
Distance_MA60_Pct
```

Optional later:

```text
ATR14
MACD
Bollinger Bands
```

Do not add indicators without a defined analytical purpose.

---

# 9. RSI Engine

Interpretation:

```text
RSI >= 80     highly stretched
70–80         strong / overheated
50–70         positive momentum
30–50         weak momentum
< 30          oversold
```

Detect:

```text
cross above 30
cross above 50
cross above 70
cross below 70
cross below 50
cross below 30

bullish divergence
bearish divergence
```

Important:

RSI measures momentum, not valuation.

Divergence detection must use confirmed corresponding price and RSI pivots.

---

# 10. Price Structure Engine

Detect swing highs and lows.

Classify:

```text
HH = Higher High
HL = Higher Low
LH = Lower High
LL = Lower Low
```

Every classification must retain:

```text
date
price
pivot_type
comparison_date
comparison_price
```

Example:

```text
2026-08-31 Low = 97.2
2026-09-07 Low = 103.5

Result = Higher Low
```

Never output “Higher Low” without the supporting prices and dates.

Possible structure states:

```text
UPTREND_STRUCTURE
DOWNTREND_STRUCTURE
POSSIBLE_BASE
POSSIBLE_TOP
RANGE
UNCONFIRMED
```

Pivot sensitivity must be configurable.

---

# 11. Volume Engine

Evaluate combinations:

```text
Price ↓ + Volume ↑
Price ↓ + Volume ↓
Price ↑ + Volume ↑
Price ↑ + Volume ↓

Breakout + Volume ↑
Breakdown + Volume ↑
```

Use Volume Ratio:

```text
Volume_Ratio_20 = Today Volume / 20D Average Volume
```

Default configurable thresholds:

```text
< 0.7x      quiet
0.7–1.3x    normal
1.3–1.8x    elevated
> 1.8x      unusually high
```

High volume alone must never be labeled “distribution”.

---

# 12. Institutional Engine

Analyze separately:

```text
Foreign
Investment Trust
Dealer
```

Windows:

```text
1D
3D
5D
10D
20D
```

Detect:

```text
persistent buying
persistent selling
selling pressure decreasing
buying pressure decreasing
sell → buy transition
buy → sell transition
```

Do not use one positive/negative day as a trend conclusion.

---

# 13. Margin Engine

Interpret combinations:

```text
Price ↓ + Margin ↑
→ left-side leverage accumulation / potential pressure

Price ↓ + Margin ↓
→ deleveraging / possible cleanup

Price ↑ + Margin ↑
→ participation rises but leverage risk also rises

Price ↑ + Margin ↓
→ potentially healthier participation structure
```

Important:

Margin balance is a **stock**, not a cost distribution.

The dashboard should flag unusually rapid 20D margin expansion.

---

# 14. Support / Resistance Engine

Use:

- confirmed swing highs;
- confirmed swing lows;
- consolidation zones;
- high-volume price areas where available;
- MA20;
- MA60;
- breakout / breakdown levels.

Output:

```text
support_1
support_2

resistance_1
resistance_2
```

Detect:

```text
Resistance → Support
Support → Resistance
```

Each level must include its derivation.

Example:

```text
Support = 110

Evidence:
- previous resistance
- breakout on YYYY-MM-DD
- successful retest on YYYY-MM-DD
```

---

# 15. Seven-Factor Evidence Matrix

Statuses:

```text
BULLISH
NEUTRAL
BEARISH
WARNING
INSUFFICIENT_DATA
```

Do not convert the matrix into one stock score.

Example:

| Factor | Status | Evidence |
|---|---|---|
| Price Structure | BULLISH | HH + HL |
| RSI | WARNING | RSI 74 |
| MA | BULLISH | MA5 > MA20 > MA60 |
| Volume | NEUTRAL | 1.1× 20D average |
| Foreign | BULLISH | 5D positive |
| Margin | WARNING | 20D +34% |
| S/R | BULLISH | key support intact |

Store structured evidence:

```text
factor
status
headline
observations
reasoning
source_dates
updated_at
```

---

# 16. Market Stage Engine

Allowed stages:

```text
A_DOWNTREND
B_EARLY_BASE
C_BASE_CONFIRMATION
D_UPTREND
E_OVERHEATED
F_HIGH_LEVEL_CORRECTION
G_STRUCTURE_WEAKENING
TRANSITION
UNCLASSIFIED
```

## A — Downtrend

Typical:

```text
LH + LL
MA20 falling
price below MA20
weak rebounds
institutional selling
```

## B — Early Base

Typical:

```text
new lows slowing/stopping
RSI recovering from oversold
volume contraction
institutional selling pressure declining
```

## C — Base Confirmation

Typical:

```text
Higher Low
break above reaction high
MA5 turning upward
RSI > 50
breakout participation improves
```

## D — Uptrend

Typical:

```text
HH + HL
MA5 > MA20
MA20 rising
RSI roughly 50–70
support retests hold
```

## E — Overheated

Typical:

```text
rapid appreciation
RSI > 70–80
large MA20 deviation
elevated volume
rapid margin expansion
```

Overheated does **not** mean immediate reversal.

## F — High-Level Correction

Typical:

```text
RSI falls from elevated level
price loses MA5 / MA20
rebound forms LH
institutional flows weaken
support comes under pressure
```

## G — Structure Weakening

Typical:

```text
LH + LL
important support breaks
reclaim fails
institutional selling persists
```

Transitions are valid:

```text
B → C
C → D
D → E
E → F
F → G
```

---

# 17. Change Detection — Core Feature

This is a core product feature.

Compare every valid daily snapshot against the previous valid snapshot.

Detect:

```text
Market Stage changed

RSI crossed:
30
50
70
80

MA5 crossed MA20

Price crossed:
MA20
MA60

New:
HH
HL
LH
LL

Support:
broken
reclaimed

Resistance:
broken
failed breakout

Foreign 5D changed sign
Trust 5D changed sign

Margin acceleration

Volume Ratio threshold crossed
```

Store:

```text
ticker
date
change_type
severity
previous_value
current_value
explanation
```

Severity:

```text
INFO
WATCH
IMPORTANT
CRITICAL
```

Severity is an attention mechanism, not a buy/sell rating.

---

# 18. Daily Snapshot

Store one analysis snapshot per ticker per market date:

```text
ticker
date
close

market_stage
structure_state
latest_pivot_type

rsi14

ma5
ma20
ma60

volume_ratio_20

foreign_5d
foreign_20d

trust_5d
trust_20d

dealer_5d

margin_balance
margin_change_5d
margin_change_20d
margin_change_pct_20d

support_1
support_2
resistance_1
resistance_2

bullish_evidence_count
bearish_evidence_count
warning_count

data_quality_status
created_at
```

This allows historical state changes to be audited.

---

# 19. Database

Minimum DuckDB tables:

```text
stocks
holdings

ohlcv_daily
institutional_daily
margin_daily

fundamentals_monthly
fundamentals_quarterly

corporate_actions

indicator_daily
price_pivots
support_resistance

evidence_daily
market_stage_daily
change_events

data_quality_events
```

Use `ticker + market_date` keys where appropriate.

---

# 20. Dashboard — Portfolio Radar

This is the default landing page.

Goal:

> Show which holdings require attention today.

Top cards:

```text
Total Holdings
Stage Changes Today
Important Alerts
Data Quality Warnings
Last Data Update
```

Main table:

| Stock | Price | Cost | P/L | Stage | RSI | Structure | MA | Foreign 5D | Trust 5D | Margin 20D | Key Risk | Changed? |
|---|---:|---:|---:|---|---:|---|---|---:|---:|---:|---|---|

Features:

- ticker/name search;
- stage filter;
- alert filter;
- changed-only filter;
- sortable columns;
- click row → Stock Detail.

Do not rank stocks “best to worst”.

---

# 21. Dashboard — Stock Detail Header

Show:

```text
Ticker / Name
Current Price
User Cost
P/L %
Market Stage
Latest Market Date
Data Quality
```

User cost is personal context only.

It must never alter technical support/resistance calculations.

---

# 22. Evidence Cards

Display seven cards:

```text
1. Price Structure
2. RSI
3. Moving Averages
4. Volume
5. Institutional
6. Margin
7. Support / Resistance
```

Each card shows:

```text
status
headline
current value
short explanation
expandable evidence
```

Example:

```text
MARGIN
WARNING

20D +57%

Leverage participation increased rapidly.

Evidence
- Balance: 8,550 → 13,472
- Price increased during the interval
```

---

# 23. Five-Layer Interactive Chart

The Web chart replaces the 3200×2200 PNG as the primary analytical view.

Use Plotly subplots with shared X-axis.

## Layer 1 — Price

Show:

```text
Candlestick
MA5
MA20
MA60

Support
Resistance

HH
HL
LH
LL

Important events
Market Stage regions
```

## Layer 2 — Volume

Show:

```text
Daily Volume
Volume MA20
Volume Ratio alerts
```

## Layer 3 — Institutional

Show separately:

```text
Foreign
Investment Trust
Dealer
```

Allow toggles.

## Layer 4 — Margin

Show:

```text
Margin Balance
optional daily Margin Change
```

## Layer 5 — RSI

Show:

```text
RSI14
30
50
70
80 optional
```

All five layers share the same date axis.

---

# 24. Unified Hover Inspector

Hovering one trading date should expose all relevant data.

Example:

```text
2026-08-27

OHLC
Open          105.0
High          105.5
Low           101.0
Close         101.5

Volume        21,520
Volume Ratio  1.8x

Foreign       -2,515
Trust         -17
Dealer        -2,568
Total         -5,100

Margin Δ      +703
Margin Bal    9,106

RSI14         xx.x
MA5           xx.x
MA20          xx.x
MA60          xx.x

Events
- support broken
- institutional selling elevated
- margin increased while price fell
```

The goal is to let the user verify why the system generated an event.

---

# 25. Chart Controls

Time ranges:

```text
20D
60D
120D
6M
1Y
MAX
```

Support:

- zoom;
- pan;
- reset;
- synchronized hover;
- MA toggles;
- institutional toggles;
- support/resistance toggles;
- event toggles;
- Market Stage overlay toggle.

Avoid large permanent annotation boxes.

Use compact event markers with hover/click details.

---

# 26. Market Stage Timeline

Provide a dedicated timeline.

Example:

```text
07/20  Early Base
07/30  Base Confirmation
08/05  Uptrend
08/10  Uptrend → Overheated
08/14  High-Level Correction
08/20  Structure Weakening
08/31  Early Base
09/10  Base Confirmation
09/17  Uptrend
09/24  Uptrend → Overheated
```

Clicking a transition must show:

```text
Why did the state change?

Added evidence:
+ RSI crossed above 50
+ Higher Low confirmed
+ MA5 slope became positive

Removed evidence:
- institutional selling pressure

Still unresolved:
- margin leverage elevated
```

---

# 27. Yesterday vs Today

This is a high-priority feature.

Example:

| Metric | Yesterday | Today |
|---|---:|---:|
| Stage | D | D → E |
| RSI | 68 | 74 |
| Structure | HH/HL | HH/HL |
| MA | Bullish | Bullish |
| Volume Ratio | 1.0× | 1.7× |
| Foreign 5D | +4,000 | +5,000 |
| Trust 5D | +800 | -200 |
| Margin 20D | +28% | +34% |
| Support | Intact | Intact |

Then show:

```text
New Risks
Resolved Risks
New Bullish Evidence
New Bearish Evidence
```

This should answer:

> What changed since the previous trading day?

---

# 28. Compare Holdings

Allow 2–5 holdings to be compared.

Compare:

```text
Market Stage
RSI14
20D Return
Distance from MA20
Volume Ratio
Foreign 5D / 20D
Trust 5D / 20D
Margin 20D %
Distance to Support
Distance to Resistance
```

Do not produce an overall ranking or winner.

Purpose:

> Side-by-side evidence inspection.

---

# 29. Timeline / Historical Review

Allow the user to select:

```text
Stock
Date Range
Historical Snapshot
```

Show:

- stage changes;
- alerts;
- old Evidence Matrix;
- support/resistance at that time;
- indicator state at that time.

Critical rule:

> Historical review must not use future data.

The system should be able to answer:

> What did the system know on that date?

---

# 30. No Look-Ahead / Pivot Policy

Pivot detection creates a special issue because a swing high/low often requires future bars for confirmation.

Therefore store:

```text
pivot_date
confirmation_date
```

Distinguish:

```text
REAL_TIME_SIGNAL
RETROSPECTIVE_ANNOTATION
```

Historical snapshots may only use pivots that were confirmed by that snapshot date.

Never leak future confirmation into historical analysis.

---

# 31. Data Quality Page

Display:

| Ticker | Dataset | Latest Date | Source | Status | Missing | Conflicts | Retrieved |
|---|---|---|---|---|---|---|---|

Allow inspection of:

```text
PASS
PASS_WITH_WARNINGS
FAIL
```

A beautiful dashboard built on incorrect data is useless.

Data Quality is therefore a first-class page.

---

# 32. Portfolio Configuration

Use:

```text
config/holdings.yaml
```

Example:

```yaml
holdings:
  - ticker: "3702"
    name: "大聯大"
    cost: 108.0
    quantity_lots: 10
    horizon: "swing"

  - ticker: "2330"
    name: "台積電"
    cost: null
    quantity_lots: null
    horizon: "long"
```

Important:

If user cost = 120, the system must not call 120 “support” merely because that is the user's break-even price.

---

# 33. Conditional Decision Framework

The system should explain conditions rather than issue certainty.

Example:

```text
Current Stage
UPTREND → OVERHEATED

Trend Evidence
+ HH + HL
+ MA5 > MA20 > MA60
+ Foreign 5D positive

Risk Evidence
- RSI 74
- Margin 20D +34%
- Volume Ratio 1.7x

Structure remains intact while:
- support 110 holds

Evidence of deterioration would include:
- rebound fails
- Lower High appears
- 110 breaks
- Foreign 5D turns negative
```

Avoid:

```text
BUY NOW
SELL NOW
90% probability of rise
guaranteed target
```

---

# 34. Optional Strategy Labels

If useful, display observational actions such as:

```text
WAIT_FOR_CONFIRMATION
MONITOR_SUPPORT
TREND_INTACT
OVERHEAT_WATCH
STRUCTURE_WARNING
DATA_INSUFFICIENT
```

These are monitoring states, not investment recommendations.

---

# 35. Export System

The Dashboard is primary.

Exports are secondary.

Provide:

```text
Export CSV
Export PNG
Export PDF
```

## PNG

Generate on demand.

Minimum target:

```text
3200 × 2200
```

Include:

- five-layer chart;
- seven Evidence Cards;
- Market Stage;
- key support/resistance;
- important change events;
- source/date metadata.

The PNG must use the exact same data and analysis snapshot as the Dashboard.

Never use image generation to fabricate financial charts.

## PDF

Later phase.

Use the same snapshot/evidence objects.

---

# 36. Refresh Workflow

Provide:

```text
[ Update Market Data ]
```

Flow:

```text
Fetch
 ↓
Normalize
 ↓
Validate
 ↓
Persist
 ↓
Calculate Indicators
 ↓
Run Analysis
 ↓
Create Snapshot
 ↓
Detect Changes
 ↓
Refresh Dashboard
```

Do not fetch remote data every time Streamlit reruns.

---

# 37. Caching / Performance

Target:

```text
1–100 holdings
```

Requirements:

- dashboard reads from DuckDB;
- remote fetching is separate from rendering;
- incremental updates;
- cache reference data;
- do not redownload complete history when only one day is missing.

Use Streamlit caching carefully.

---

# 38. Explainability

Every conclusion must be traceable.

Example:

```text
Stage = BASE_CONFIRMATION

Evidence:
1. 2026-08-31 Low = 97.2
2. 2026-09-07 Low = 103.5
   → Higher Low
3. RSI crossed above 50 on YYYY-MM-DD
4. Price closed above reaction high
5. MA5 slope became positive
```

Never show:

```text
AI believes the stock is building a base.
```

without evidence.

---

# 39. Rule Engine Before LLM

Architecture:

```text
Raw Data
 ↓
Deterministic Calculations
 ↓
Rule Engine
 ↓
Structured Evidence
 ↓
Optional LLM Explanation
```

LLM may:

- summarize;
- explain terminology;
- turn structured evidence into readable commentary.

LLM may not:

- invent missing values;
- overwrite calculated RSI/MA;
- fabricate pivots;
- silently alter Market Stage;
- fabricate institutional/margin data.

---

# 40. Evidence Object

Example:

```json
{
  "factor": "margin",
  "status": "WARNING",
  "headline": "Margin balance increased rapidly",
  "observations": [
    {
      "metric": "margin_change_pct_20d",
      "value": 57.0,
      "unit": "%"
    }
  ],
  "reasoning": "Price rose while leverage participation accelerated.",
  "source_dates": [
    "2026-08-26",
    "2026-09-24"
  ]
}
```

The same object feeds:

```text
Evidence Card
Change Detection
Report
PNG Export
PDF Export
```

---

# 41. Event Model

Event types:

```text
PIVOT_HIGH
PIVOT_LOW

HIGHER_HIGH
HIGHER_LOW
LOWER_HIGH
LOWER_LOW

SUPPORT_BREAK
SUPPORT_RECLAIM
RESISTANCE_BREAK
FAILED_BREAKOUT

RSI_OVERBOUGHT
RSI_OVERSOLD
RSI_50_CROSS_UP
RSI_50_CROSS_DOWN

MA5_MA20_CROSS_UP
MA5_MA20_CROSS_DOWN

FOREIGN_FLOW_REVERSAL
TRUST_FLOW_REVERSAL

MARGIN_ACCELERATION
VOLUME_EXPANSION

MARKET_STAGE_CHANGE
```

Fields:

```text
ticker
date
event_type
severity
headline
details_json
```

---

# 42. Testing

Required unit tests:

```text
RSI
Moving Averages
Volume Ratio

Institutional rolling sums
Margin changes

Pivot detection
HH / HL / LH / LL

Support / Resistance

Market Stage rules
Change Detection

Data Validation
```

Use regression fixtures with manually verified real Taiwan-stock data.

For a regression fixture:

1. verify raw data first;
2. lock expected raw values;
3. test indicators;
4. test interpretation.

---

# 43. Logging

Structured events:

```text
DATA_FETCH_START
DATA_FETCH_SUCCESS
DATA_FETCH_FAIL

VALIDATION_WARNING
VALIDATION_FAIL

ANALYSIS_COMPLETE

STAGE_CHANGE

EXPORT_COMPLETE
```

Logs should make source failures easy to diagnose.

---

# 44. Development Phases

## Phase 0 — Foundation

Deliver:

```text
Repository
Dependencies
Configuration
DuckDB
Models
Logging
pytest
Streamlit shell
```

Acceptance:

```text
pytest runs
Streamlit boots
DuckDB initializes
config loads
```

---

## Phase 1 — Real OHLCV + 3-Layer Interactive Chart

Implement:

```text
official OHLCV source
validation
DuckDB persistence

MA5
MA20
MA60
RSI14
Volume MA20
Volume Ratio
```

Stock Detail chart:

```text
Layer 1: Candlestick + MA
Layer 2: Volume
Layer 3: RSI
```

Controls:

```text
20D / 60D / 120D / 1Y
```

Acceptance:

- use real 3702 data;
- manually verify at least 10 dates;
- indicator tests pass;
- hover shows exact raw data;
- no fake/sample values in production path.

Do not proceed until reliable.

---

## Phase 2 — Institutional + Margin

Add:

```text
Foreign
Investment Trust
Dealer
Margin
Short
```

Extend chart to full five layers.

Acceptance:

- source dates verified;
- units verified;
- random-date spot checks;
- rolling calculations tested;
- unified hover works.

---

## Phase 3 — Price Structure

Implement:

```text
Pivots
HH
HL
LH
LL
Support
Resistance
```

Acceptance:

- every structure contains date/price evidence;
- pivot confirmation date stored;
- no-look-ahead tests pass.

---

## Phase 4 — Evidence Engine

Implement seven Evidence Cards.

Acceptance:

- each card links to evidence;
- missing data → INSUFFICIENT_DATA;
- no single buy/sell score.

---

## Phase 5 — Market Stage Engine

Implement:

```text
Downtrend
Early Base
Base Confirmation
Uptrend
Overheated
High-Level Correction
Structure Weakening
Transition
```

Acceptance:

- deterministic;
- reason list available;
- transition tests pass.

---

## Phase 6 — Snapshot + Change Detection

Implement:

```text
Daily Snapshot
Yesterday vs Today
Stage Change
Indicator Change
Risk Events
```

Acceptance:

- reproducible snapshots;
- stage history persists;
- changed holdings filter works.

**This is a critical phase.**

---

## Phase 7 — Portfolio Radar

Implement complete home page.

Acceptance:

- 1–100 holdings;
- fast DB rendering;
- filters;
- search;
- changed-only mode;
- row → Stock Detail navigation.

---

## Phase 8 — Timeline + Compare + Data Quality

Implement remaining pages.

Acceptance:

- historical snapshots;
- Market Stage Timeline;
- side-by-side comparison;
- data-quality audit.

---

## Phase 9 — Export

Implement:

```text
CSV
High-resolution PNG
PDF optional
```

Acceptance:

- export matches Dashboard snapshot exactly;
- sources/dates included;
- no fabricated chart values.

---

## Phase 10 — Fundamentals

Implement:

```text
Revenue
YoY
EPS
Gross Margin
Operating Margin
Net Margin
```

Optional:

```text
ROE
FCF
Dividend
Yield
PE
PB
```

Goal:

Determine whether a price decline is occurring with or without fundamental deterioration.

---

# 45. UI Priority

Development priority:

```text
1. Data correctness
2. Stock Detail interactive chart
3. Evidence Cards
4. Change Detection
5. Portfolio Radar
6. Market Stage Timeline
7. Data Quality
8. Compare
9. Export
10. Cosmetic polish
```

Do not spend early development time making the dashboard visually beautiful while data validation is incomplete.

---

# 46. Definition of Done

The system is considered practically usable when:

- holdings are configured once;
- market data updates with one action;
- Portfolio Radar shows changed holdings;
- each stock has a five-layer synchronized chart;
- each stock has seven Evidence Cards;
- each stock has an explainable Market Stage;
- daily snapshots are persisted;
- Yesterday vs Today works;
- Market Stage Timeline works;
- Data Quality issues are visible;
- historical analysis has no look-ahead leakage;
- PNG export is optional rather than primary;
- no production analysis uses fabricated market data.

---

# 47. FIRST CODEX TASK

**Codex must not implement the whole project at once.**

Read this entire document first.

Then implement **Phase 0 + Phase 1 only**.

Exact task:

```text
Read IMPLEMENT_PLAN_WEB_DASHBOARD_V2.md completely.

Implement Phase 0 and Phase 1 only.

Create a local Streamlit + Plotly + DuckDB application.

Requirements:

1. Initialize the repository structure.

2. Configure Python dependencies.

3. Initialize DuckDB.

4. Implement configuration loading.

5. Implement one reliable Taiwan-stock OHLCV provider.

6. Retrieve real OHLCV data.

7. Normalize and validate OHLCV.

8. Persist normalized OHLCV in DuckDB.

9. Calculate:
   - MA5
   - MA20
   - MA60
   - RSI14
   - Volume MA20
   - Volume Ratio 20

10. Create the Stock Detail page.

11. Render:
   Layer 1:
   - Candlestick
   - MA5
   - MA20
   - MA60

   Layer 2:
   - Volume
   - Volume MA20

   Layer 3:
   - RSI14
   - RSI 30 / 50 / 70 reference levels

12. All layers must share the same date axis.

13. Add:
   - 20D
   - 60D
   - 120D
   - 1Y
   range controls.

14. Hover must show exact market values.

15. Use 3702 大聯大 as the initial regression ticker.

16. Add indicator and validation unit tests.

17. Add README instructions.

Before declaring Phase 1 complete:

- verify at least 10 OHLCV dates against the actual source;
- record source metadata and retrieval timestamp;
- ensure no generated/sample/fake market values are used in production;
- run pytest;
- report test results;
- report any source limitations.

Do NOT implement yet:

- institutional flows;
- margin;
- HH/HL/LH/LL;
- Evidence Matrix;
- Market Stage;
- AI explanation.

If an official data source is unavailable or ambiguous, document the blocker rather than silently substituting fabricated data.
```

---

# 48. SECOND CODEX TASK

Only after Phase 1 passes:

```text
Implement Phase 2.

Add real institutional and margin datasets.

Extend Stock Detail to five synchronized Plotly layers:

1. Candlestick + MA5/20/60
2. Volume + Volume MA20
3. Foreign / Investment Trust / Dealer
4. Margin Balance
5. RSI14

Implement unified date inspection.

For each dataset:

- normalize units;
- store source metadata;
- validate random dates;
- add regression tests.

Do not implement Market Stage until Phase 2 data quality is proven.
```

---

# 49. THIRD CODEX TASK

Only after Phase 2 passes:

```text
Implement Phase 3 and Phase 4.

Phase 3:
- swing highs/lows
- HH / HL / LH / LL
- pivot_date
- confirmation_date
- no-look-ahead handling
- support / resistance

Phase 4:
- seven-factor Evidence Matrix
- seven Evidence Cards
- structured evidence objects

Every conclusion must be traceable to real dates and values.

Do not implement Market Stage until structure and evidence regression tests pass.
```

---

# 50. FOURTH CODEX TASK

After Phase 3/4 pass:

```text
Implement Phase 5 and Phase 6.

Phase 5:
Market Stage Engine

Phase 6:
Daily Snapshot + Change Detection

Prioritize:
- Yesterday vs Today
- Market Stage transitions
- new HH/HL/LH/LL
- RSI threshold changes
- support breaks/reclaims
- institutional flow reversals
- margin acceleration

The Portfolio page must be able to show only holdings with meaningful new changes.
```

---

# 51. Final Product Principle

The application should make the user better at reviewing evidence rather than becoming dependent on a black-box prediction.

Every day, the Dashboard should help answer:

> **What changed?**

> **What evidence supports the current interpretation?**

> **What evidence contradicts it?**

> **Which market structure would invalidate it?**

> **Is current risk coming from price structure, momentum, trend, volume, institutional flow, leverage, or fundamentals?**

The goal is not:

> “Predict tomorrow's stock price.”

The goal is:

> **Build a repeatable, auditable process for monitoring portfolio market structure and risk.**
