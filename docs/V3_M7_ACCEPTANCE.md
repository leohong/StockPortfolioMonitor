# V3 M7 驗收紀錄

驗收日期：2026-09-26  
正式規則版本：`m7-significance-scenario-v1`  
Schema：13  
程式提交：`2268948`

## 實作範圍

- Significance Engine：比較相鄰 M6 evidence vector 與 Market State，只為實際狀態變化建立事件。
- 每個事件保存 deterministic event ID、前後狀態、LOW／MEDIUM／HIGH／CRITICAL、當日 context features、reason codes 與說明。
- Scenario Engine：每天固定建立 `POSITIVE_CONTINUATION`、`NEUTRAL_UNRESOLVED`、`NEGATIVE_DETERIORATION`。
- 每個 scenario 保存結構化條件、實際觀測、是否符合、確認事件、失效事件、相關價位與 evidence dependencies。
- 未實作 M8 UI cutover。

## 重要性規則

- HIGH：結構狀態變化、跌破區或進入 S8 結構失敗。
- MEDIUM：Market State、regime、trend、capital flow、positioning、location 等脈絡變化。
- LOW：momentum、relative strength、participation 等次層證據變化。
- CRITICAL：必須同時具備支撐跌破、下降結構、量能確認、負向法人流向，以及槓桿擴張／擁擠／壓力。單一高量或單一指標不能產生 CRITICAL。

Significance 只表示檢視優先度，不代表買賣建議，也不是總分。

## 正式資料驗收

3702 的 304 日 M6 evidence 產生：

- 690 個狀態變化事件，日期範圍 2025-07-18 至 2026-09-24。
- HIGH 29、MEDIUM 429、LOW 232；正式期間沒有同時滿足完整組合的 CRITICAL 事件，因此沒有強制產生 CRITICAL。
- 912 個 scenario，涵蓋 304 個交易日；三種類型各 304 筆。
- 相同 ruleset 重跑後事件與 scenario 筆數不變，持久化具冪等性。
- V2 `analysis_snapshots` 維持 304 筆，最新日期仍是 2026-09-24。

2026-09-24 的事件：

- Location：`AT_SUPPORT` → `NEAR_SUPPORT`，MEDIUM。
- Participation：`NORMAL` → `WEAK_CONFIRMATION`，LOW。

當日 scenario：

- Continuation：`PARTIAL`。Trend Emerging、RS Improving、Location 未跌破成立；Uptrend Structure 未成立。
- Unresolved：`SUPPORTED`。Market State 為 Transition，且 sector regime 與 fundamental context 仍不足。
- Deterioration：`PARTIAL`。下降結構成立；Trend Broken、負向 flow 與支撐跌破未成立。

## 無預測與結構化引用檢查

- 三種 scenario 都是條件式敘述，沒有上漲／下跌機率。
- 沒有目標價或未經支撐的價格預測。
- 每個條件都包含 dimension、operator、expected、observed、satisfied。
- confirmation／invalidation event 都列出依賴維度。
- 正式資料庫禁用字樣檢查結果為 0 筆。

## 測試

- 完整測試：`100 passed in 7.87s`。
- 測試涵蓋 deterministic event ID、HIGH 結構事件、CRITICAL 組合門檻、三種 scenario、結構化條件、確認／失效事件，以及禁止機率與目標價。

## 已知限制

- 正式期間沒有符合完整 CRITICAL 組合的案例；規則以人工構造的邊界測試驗證，M9 仍需用更長歷史做事件研究。
- Scenario 表達目前條件是否成立，不推估未來發生機率。
- Fundamental context 與 sector regime 的既有缺值會使 unresolved scenario 持續成立；系統不以推測資料補足。
