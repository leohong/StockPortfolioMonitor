# V3 Migration Report

完成日期：2026-09-26

## 遷移結果

V3 M0 至 M9 已依序完成。V2 Phase 0 至 Phase 9 的資料表、模型、介面、五層圖表與匯出路徑仍保留；V3 以 additive migrations、獨立 ruleset、獨立 snapshot 與獨立 UI 查詢共存，沒有機械轉換或覆寫 V2 歷史。

| 階段 | 交付內容 |
|---|---|
| M0 | Repository audit、baseline、風險與相依性盤點 |
| M1 | Analysis version、V3 models、additive schema、V2/V3 coexistence |
| M2 | 官方 TAIEX benchmark、Market Regime、point-in-time sector context |
| M3 | Trend Quality、Momentum V3、Relative Strength |
| M4 | Participation、Flow Persistence、Positioning |
| M5 | Volatility、AVWAP、Location／Confluence |
| M6 | 12 維 Evidence Vector、hierarchical Market State、V3 snapshot |
| M7 | Significance Engine、三種條件式 Scenario |
| M8 | V3 UI cutover、V2 歷史入口、V3 export |
| M9 | Replay、event study、walk-forward、robustness、performance、遷移決策 |

## 資料與版本

- V2 `analysis_snapshots`：3702 共 304 筆，2025-07-01 至 2026-09-24。
- V3 `snapshot_v3_daily`：同期間 304 筆，ruleset `m6-evidence-market-state-v1`。
- M7：690 個事件、912 個 scenario，ruleset `m7-significance-scenario-v1`。
- Schema version：13；M9 沒有 DB migration，也沒有新增正式分析表。
- M9 評估直接使用官方取得、驗證並持久化的資料；沒有下載、插值或補造資料。

## 相容性與驗收

- P1–P9 regression suite 保留。
- V2 history 可稽核且未被改寫。
- V3 snapshot 有 analysis/ruleset version，identity immutable。
- Dashboard 預設 V3，仍可存取 V2 timeline、comparison、CSV 與 PNG。
- V3 CSV 重現同一份 snapshot、事件與 scenario。
- 304 日 replay 沒有 evidence/state/event/scenario mismatch，也沒有 future-source violation。
- 缺少的 sector、breadth、fundamental context 保持 `INSUFFICIENT_DATA`。

## 尚存限制

- 正式 holdings 只有 3702，跨股票比較只由測試驗證。
- 官方 normalized rows 沒有完整 revision history，無法重播後來被官方修訂前的原始版本。
- Sector benchmark、market breadth、point-in-time fundamentals 尚無足夠官方歷史來源。
- Walk-forward 結果不支持方向預測用途。
- M9 沒有移除 V2；後續若擴充資料或規則，必須建立新 ruleset，不得覆寫既有 V3 snapshot。
