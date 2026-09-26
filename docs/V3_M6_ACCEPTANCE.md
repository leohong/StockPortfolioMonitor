# V3 M6 驗收紀錄

驗收日期：2026-09-26  
正式規則版本：`m6-evidence-market-state-v1`  
Schema：12  
程式提交：`f846bd6`

## 實作範圍

- Evidence Vector：regime、sector regime、structure、trend、momentum、relative strength、participation、capital flow、positioning、volatility、location、fundamental context，共 12 維。
- 每個維度保存 state、headline、observations、支持與反向證據、缺失資料、來源日期及該維度原始 calculation version。
- Market State V3：固定階層規則、前一狀態、transition、主要／支持／反向證據、失效條件及未解問題。
- 每日獨立保存 `evidence_v3_daily`、`market_state_v3_daily` 與完整 `snapshot_v3_daily`；沒有改寫 V2 快照。
- 未加入 M7 的 significance 或 scenario。

## 階層規則

判定順序為資料品質、結構失敗、下降、組合型 distribution risk、修正、延伸、突破、趨勢、築底、穩定及 transition。低層證據只能支持或反駁，不能以加權投票推翻破壞的價格結構。

系統沒有總分、星等、買賣標籤或上漲機率。`S6_DISTRIBUTION_RISK` 必須同時有異常／矛盾 participation，以及負向 flow 或擁擠／壓力 positioning；單獨高量不會被稱為 distribution。

## Point-in-time replay

- 以既有 M2–M5 每日持久化結果組合 2025-07-01 至 2026-09-24 的 304 日 evidence、state 與 snapshot。
- 每個維度若包含晚於分析日的來源日期，會轉為 `INSUFFICIENT_DATA` 並標記 `future_source_date_rejected`。
- 正式 304 日結果的未來來源日期違規為 0。
- 相同 ruleset 與相同原始資料連續重播兩次成功；三個 M6 資料表均維持 304 筆，沒有重複或內容漂移。

歷史狀態分布：S0 下降 8 日、S1 穩定 27 日、S2 築底 17 日、S3 突破 8 日、S4 趨勢 28 日、S5 延伸 17 日、S6 distribution risk 11 日、S7 修正 8 日、S8 結構失敗 5 日、transition 175 日。

## 3702 最新結果

2026-09-24 的 Market State 為 `TRANSITION`：

- 主要證據：`DOWNTREND_STRUCTURE`、`TREND_EMERGING`、`ACCELERATING`，結構與近期趨勢／動能尚未一致。
- 支持證據：市場 `RISK_ON_TREND`、相對強弱 `IMPROVING`、法人流向 `POSITIVE`。
- Positioning 為 `LEVERAGE_EXPANDING`、Participation 為 `WEAK_CONFIRMATION`、Volatility 為 `NORMAL`、Location 為 `NEAR_SUPPORT`。
- 未解資料：fundamental context、市場 breadth、sector benchmark，以及分析日可用的 sector classification。缺值保持缺值。

## V2/V3 並行與測試

- V2 `analysis_snapshots` 仍為 304 筆，最新日期仍是 2026-09-24。
- V3 同期有 304 筆 evidence、304 筆 market state、304 筆完整 snapshot。
- 完整測試：`97 passed in 8.60s`。
- 測試涵蓋 12 維 schema、無總分、階層優先序、組合型 distribution risk、支持與反向證據、失效條件、狀態轉換、未來來源阻擋、V2/V3 共存及 snapshot 不可變性。

## 已知限制

- Fundamental context 尚無正式 point-in-time 資料，依計畫保持 `INSUFFICIENT_DATA`。
- 2026-09-24 當日沒有可用的 sector classification／sector benchmark，sector regime 保持資料不足。
- Market State 是描述性規則狀態，不是預測；狀態 significance 與條件式 scenario 留待 M7。
