# V3 M4 驗收紀錄

驗收日期：2026-09-26  
正式規則版本：`m4-participation-flow-positioning-v2`  
Schema：10  
程式提交：`a3c93e4`

## 實作範圍

- Participation：保存 5／20 日均量、20 日量比、成交金額、日內收盤位置，以及相對於前 20 個交易日區間的突破／跌破。
- Flow Persistence：外資、投信、自營商分開保存 1／3／5／10／20 日淨買賣超、10 日正負天數與持續度。
- Positioning：保存融資 5／10／20 日變化及變化率、融券變化、20 日價格報酬、成交金額背景與槓桿背離。
- 三套引擎都產生結構化 observations、缺值欄位及實際來源日期。未加入 M5 的波動、AVWAP 或 Location 功能。

## 正式資料驗收

正式流程只讀取既有、已驗證並持久化的證交所官方資料，沒有新增 provider 或網路下載路徑：

| 原始資料 | 3702 筆數 | 單位 | 官方標記 |
|---|---:|---|---|
| OHLCV | 304 | 成交量 `shares`、成交金額 `TWD` | 全部 true |
| 三大法人 | 250 | `shares` | 全部 true |
| 融資融券 | 250 | `trading_units` | 全部 true |

正式 ruleset 的輸出：Participation 304 筆（2025-07-01 至 2026-09-24）、Flow 750 筆（250 日 × 3 類法人）、Positioning 250 筆（2025-09-15 至 2026-09-24）。V2 `analysis_snapshots` 仍為 304 筆，最新日期仍為 2026-09-24。

3702 在 2026-09-24 的代表性結果：

- Participation：`WEAK_CONFIRMATION`。收盤突破前 20 日高點、CLV 1.0，但量比只有 0.8835，沒有把高量單獨解讀為出貨。
- 外資：`PERSISTENT_BUYING`，10 日淨買超 12,138,842 股，正向 8/10 日，持續度 0.8。
- 投信：`REVERSING_POSITIVE`，3 日淨買超 21,000 股，20 日仍為淨賣超 590,468 股。
- 自營商：`REVERSING_POSITIVE`，3 日淨買超 75,831 股，10 日仍為淨賣超 285,705 股。
- Positioning：`LEVERAGE_EXPANDING`。融資 20 日增加 47.9464%，價格上漲 15.7635%，槓桿背離 32.1829 個百分點；當日成交金額比為 0.9620，未達擁擠規則所需的 1.2。

## 規則與門檻

`config/settings.yaml` 可調整 Participation 確認／強確認／異常量比、Flow 10 日持續度、Positioning 融資擴張／擁擠／去槓桿門檻。判定只使用當日及更早的列；突破區間以 `rolling(20).shift(1)` 排除當日，20 日變化以 20 個交易日前的真實觀測計算。

`m4-participation-flow-positioning-v1` 在首次正式驗證時發現 `volume_ratio_20` 的 observation 單位誤標為 `shares`；數值與狀態未受影響。依版本不可變原則保留該列，修正後以 v2 ruleset 重新產生正式結果，ratio 現為正確的無量綱標記。

## 測試與相容性

- 完整測試：`88 passed in 6.91s`。
- 測試涵蓋突破參與、僅高量不得稱為 distribution、三類法人持續／反轉、槓桿背離與原始單位。
- 舊有 Streamlit、法人、融資融券及 V2/V3 共存測試全部通過。

## 已知限制

- 法人及融資融券只有 250 個交易日，因此比 304 日 OHLCV 較短；較早日期維持資料不足，不補值。
- 門檻是第一版可設定的描述性規則，需留待 M9 用歷史 walk-forward 與參數穩健性檢查；目前狀態不代表買賣建議。
- 融資融券維持官方交易單位，不能直接與法人股數相加或比較絕對量。
