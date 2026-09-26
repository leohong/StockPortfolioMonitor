# V3 M8 驗收紀錄

驗收日期：2026-09-26  
V3 snapshot 規則版本：`m6-evidence-market-state-v1`  
事件與 Scenario 規則版本：`m7-significance-scenario-v1`

## 實作範圍

- Portfolio Radar 預設讀取已保存的 V3 snapshot，顯示 Regime、Market State、相對強弱、Positioning、波動、重要變化及資料品質。
- Portfolio Radar 提供 HIGH／CRITICAL、資料品質、狀態、搜尋及有變化篩選；不依單一分數排序持股。
- 個股詳情顯示 Market State 的主要、支持、反向證據、失效條件與未解問題，以及完整 12 維 evidence vector。
- 個股詳情顯示 continuation、unresolved、deterioration 三種條件式 scenario、各條件的實際觀測、確認事件、失效事件與相關價位。
- 昨日與今日、Timeline、歷史快照及持股比較改以 V3 為預設。
- 新增 V3 CSV 匯出，同時保留 V2 歷史介面、五層圖表及既有 CSV／PNG 匯出。
- 未實作 M9 的 walk-forward、事件研究、參數穩健性、效能測試或 V2 淘汰決策。

## 驗收條件

- **可檢查狀態改變原因**：個股詳情與歷史檢視顯示保存的 significance event、reason、前後狀態及 evidence；V3 昨日與今日並排列出主要維度。
- **可檢查反向證據**：Market State 區塊直接顯示 `contradicting_evidence`、`invalidation_conditions` 與 `unresolved_questions`。
- **HIGH／CRITICAL 篩選**：Portfolio Radar 篩選只保留最高重要性為 HIGH 或 CRITICAL 的最新持股；單元測試涵蓋兩種等級與排除 MEDIUM。
- **Scenario 條件可見**：三張 scenario 卡逐項顯示依賴維度、目前觀測及是否成立，並可展開確認與失效事件。
- **圖表同步**：個股 V3 區塊與既有五層圖表由同一檔持股與最新保存交易日呈現；瀏覽器驗證 3702 頁面正常顯示兩者。
- **既有匯出未退化**：原 V2 CSV 與高解析度 PNG 程式路徑及控制項保留；完整測試包含既有匯出測試並全部通過。

## 正式資料驗收

以官方資料產生並保存的 3702 歷史執行唯讀驗收：

- 最新 V3 snapshot 日期為 2026-09-24，包含 12 個 evidence 維度與 3 個 scenario。
- V3 Timeline 為 304 個交易日，日期範圍 2025-07-01 至 2026-09-24，共 74 次 Market State 改變。
- 同期 V2 `analysis_snapshots` 仍為 304 筆，日期範圍不變。
- 最新日沒有 HIGH／CRITICAL 事件，介面明確顯示 0，未製造事件以填補畫面。
- V3 CSV 包含 `v3_snapshot`、`significant_event`、`scenario` 三個 section；匯出的 Market State 與保存 payload 完全相同。
- 全程直接讀取 DuckDB 已驗證、已持久化資料，沒有重新下載、插值、推測或重算歷史 snapshot。

## 介面驗證

以 Streamlit 本機 `127.0.0.1` 驗證：

- 左側五個頁面項目完整，Timeline 標示為「V3 狀態時間軸」。
- Portfolio Radar 預設為 V3，3702 顯示已保存的 Regime、Market State、RS、Positioning 與 Volatility，並提供 V2 切換。
- 個股詳情顯示繁體中文 evidence 標籤、依固定順序排列的三種 scenario、V3 昨日與今日及 CSV 下載。
- V3 區塊下方的 V2 歷史內容與五層圖表仍正常顯示。
- Timeline 預設 V3，仍可切換 V2；歷史 V3 snapshot 直接顯示保存的 snapshot、事件與 scenario。

## 測試

- Python 語法編譯通過。
- 完整測試：`102 passed in 11.38s`。
- 新增測試涵蓋 V3 Portfolio Radar 的搜尋、狀態、有變化與 HIGH／CRITICAL 篩選，以及 V3 CSV 對 snapshot、事件、scenario 的重現。

## 已知限制

- 目前 holdings 設定只有 3702，因此正式資料無法在介面上執行 2–5 檔 V3 比較；比較服務保留 2–5 檔唯一代號限制，待加入更多具正式 V3 snapshot 的持股後使用。
- 最新交易日沒有 HIGH／CRITICAL 事件；正式資料顯示空結果，篩選邏輯由含 HIGH 與 CRITICAL 的邊界測試驗證。
- M9 才會進行較長期間的 point-in-time replay、事件研究、walk-forward、參數穩健性與 V2 淘汰評估。
