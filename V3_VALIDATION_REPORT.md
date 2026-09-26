# V3 Validation Report

驗證日期：2026-09-26  
評估版本：`m9-evaluation-v1`  
正式資料：TWSE 官方保存資料，3702 大聯大，2025-07-01 至 2026-09-24

## 結論

V3 的 304 份歷史 snapshot 通過 point-in-time 重播。Evidence Vector、Market State、690 個 significance event 與 912 個 scenario 均能從當日可用的已保存輸入重建，沒有來源日期晚於 snapshot 日期。這項結果支持快照的可稽核性與規則確定性，不代表 Market State 具有預測能力。

三個 chronological walk-forward fold 的 20 日方向一致率偏低且不穩定。正式資料只有一檔持股、304 個交易日；部分指定事件沒有樣本，volatility shock 只有 2 個完整樣本。所有事件研究只能視為描述性歷史關聯，不能用於機率、目標價或交易承諾。

## Point-in-time replay

重播依交易日排序，逐日讀取當時保存的 structure、regime、trend、momentum、relative strength、participation、capital flow、positioning、volatility 與 location，再重建 evidence、state、事件與 scenario。重播不寫入正式資料庫。

| 檢查 | 結果 |
|---|---:|
| Snapshot | 304 |
| Evidence mismatch | 0 |
| Market State mismatch | 0 |
| Event missing / extra | 0 / 0 |
| Scenario mismatch | 0 |
| Future source-date violation | 0 |
| 結果 | PASS |

本次重播驗證保存的 point-in-time component 與 M6/M7 組合規則。官方原始回應若日後修訂，既有 normalized rows 缺少逐版本 revision table，仍無法完整重建「當時下載版本」；這項 M0 已知限制沒有被隱藏。

## Event study

針對保存的狀態變化事件計算 5／10／20／60 個交易日後報酬、期間 drawdown、正報酬比例、平均值、中位數與樣本數，共產生 247 個「事件 × horizon」統計列。

| 事件 | Horizon | 樣本 | 平均報酬 | 中位報酬 | 正報酬比例 | 最差 drawdown |
|---|---:|---:|---:|---:|---:|---:|
| RS improvement | 20D | 11 | -0.09% | -4.31% | 36.36% | -20.64% |
| Margin acceleration | 20D | 15 | 2.23% | 0.42% | 53.33% | -14.09% |
| Volatility shock | 20D | 2 | 4.40% | 4.40% | 50.00% | -2.22% |

正式期間沒有 `confirmed_breakout`、`support_break` 或 capital-flow reversal 的可用事件樣本，因此不報數值，也不以其他事件替代。新 HL／LH 尚未由 M7 定義成獨立事件，不能從結構變化反推假造。

## Chronological walk-forward

使用 expanding train、接續 validation、再接續 forward test；沒有 random shuffle。每個 fold 只以 train 期間各 Market State 的 20 日平均方向，檢查後續區段方向一致率。

| Fold | Train 結束 | Validation | Forward | Validation 一致率 | Forward 一致率 |
|---|---|---|---|---:|---:|
| 1 | 2025-12-19 | 2025-12-22～2026-02-26 | 2026-03-02～2026-04-28 | 4.17%（24） | 0.00%（23） |
| 2 | 2026-02-26 | 2026-03-02～2026-04-28 | 2026-04-29～2026-06-25 | 8.00%（25） | 33.33%（12） |
| 3 | 2026-04-28 | 2026-04-29～2026-06-25 | 2026-06-26～2026-08-21 | 44.44%（36） | 46.15%（39） |

結果不支持把 V3 Market State 當作方向預測器。V3 的合格用途仍是 point-in-time 的市場結構、證據與風險決策支援。

## Parameter robustness

以鄰近門檻重算 Trend、RS、Participation、Flow、Positioning、Volatility 與 Location，共 14 組。以每日 state agreement 80% 作為「未因小幅變動而崩解」的描述性界線；14 組均高於界線。

- 最低 agreement：Volatility 較寬門檻 81.58%。
- Pivot 2／4 日相對基準 3 日：82.89%／90.79%。
- 其他 engine：91.73% 至 100%。

這只表示分類對本次鄰近值沒有全面崩解，不代表目前參數已最佳化。為避免 data snooping，實驗假設、資料期間、參數與結果記錄於 `docs/V3_EXPERIMENT_REGISTRY.json`；未用 forward test 反覆調參。

## Performance

同一台本機執行 2–3 次後取中位數。驗收參考值為 Portfolio Radar 與 event study 小於 500 ms、完整 304 日重播小於 2,000 ms。

| 操作 | 中位數 | 最大值 | 結果 |
|---|---:|---:|---|
| V3 Portfolio Radar | 35.66 ms | 35.86 ms | PASS |
| 304 日 point-in-time replay | 254.20 ms | 272.68 ms | PASS |
| Event study | 49.93 ms | 52.08 ms | PASS |

## 測試與限制

- 聚焦測試包含 future-source rejection、重播確定性、chronological split、event statistics 與 robustness sensitivity。
- 完整 regression 結果記錄於 M9 驗收文件。
- 單一股票與約 15 個月資料不足以判定跨股票、跨景氣循環的泛化能力。
- 未使用尚不存在的官方歷史 sector benchmark、breadth 或 fundamental context；缺值保持缺值。
