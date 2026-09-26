# V3 M9 驗收紀錄

驗收日期：2026-09-26  
評估版本：`m9-evaluation-v1`  
DB migration：無；Schema 維持 13

## 實作範圍

- 新增唯讀 point-in-time replay，逐日重建 Evidence Vector、Market State、significance events 與 scenarios，並與保存結果比較。
- 新增 5／10／20／60 日 event study，輸出樣本數、平均／中位報酬、正報酬比例、平均與最差 drawdown。
- 新增 expanding chronological walk-forward；train、validation、forward test 依序切分，禁止 random shuffle。
- 新增 14 組鄰近參數 robustness 檢查，涵蓋 Trend、RS、Participation、Flow、Positioning、Volatility 與 pivot sensitivity。
- 新增 Portfolio Radar、304 日 replay 與 event study 的本機 performance benchmark。
- 建立 data-snooping experiment registry，以及 V3 validation、migration、V2 deprecation 三份文件。
- 沒有刪除或標記 V2 deprecated，也沒有修改正式歷史 snapshot。

## 正式資料驗收

3702，官方保存資料 2025-07-01 至 2026-09-24：

- 304／304 份 snapshot 完成 replay。
- Evidence mismatch 0、Market State mismatch 0。
- 690 個保存事件與重建事件沒有 missing 或 extra。
- 912 個 scenario 沒有 mismatch。
- Future source-date violation 0。
- Event study 產生 247 個事件／horizon 統計列；沒有樣本的指定事件明確留空。
- 3 個 chronological walk-forward folds 完成；forward direction agreement 分別為 0.00%、33.33%、46.15%。結果不支持方向預測用途。
- 14 組鄰近參數 state agreement 均高於 80%；最低為 81.58%。這不代表參數已最佳化。
- 本機效能中位數：Portfolio Radar 35.66 ms、完整 replay 254.20 ms、event study 49.93 ms，均通過預先記錄的 500／2000／500 ms 參考值。

## 測試

- M9 聚焦測試：`6 passed in 0.67s`；另已執行 M6–M8 相依功能的擴充聚焦測試。
- 完整 regression：`108 passed in 8.10s`。
- 新增測試涵蓋未來來源拒絕、相同 as-of 輸入的確定性、chronological observation、event statistics 與 robustness collapse detection。
- M9 沒有 UI 修改，因此不需重新啟動 Streamlit 做版面驗收；M8 UI 驗收維持有效。

## 文件與決策

- `V3_VALIDATION_REPORT.md`：重播、事件研究、walk-forward、robustness、效能與限制。
- `V3_MIGRATION_REPORT.md`：M0–M9 遷移結果、版本、相容性與未解限制。
- `V2_DEPRECATION_RECOMMENDATION.md`：建議保留 V2；未滿足觀察期與明確使用者淘汰決定。
- `docs/V3_EXPERIMENT_REGISTRY.json`：固定實驗假設、期間、參數與結果，避免在同一 forward set 反覆調參。

## 已知限制

- 正式資料只有一檔股票與 304 個交易日，不能推論跨股票或跨景氣循環泛化能力。
- Point-in-time replay 從保存的 component 重建 M6/M7；normalized 官方資料缺少逐修訂版本，無法重現後來被官方修訂前的值。
- Sector benchmark、breadth 與 point-in-time fundamental context 仍沒有足夠官方歷史來源，正式流程保持缺值。
- Event association 和 walk-forward 統計不是交易策略、機率或價格預測。
