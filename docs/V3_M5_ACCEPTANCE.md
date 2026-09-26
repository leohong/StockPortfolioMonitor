# V3 M5 驗收紀錄

驗收日期：2026-09-26  
正式規則版本：`m5-volatility-location-v2`  
Schema：11  
程式提交：`fc01266`

## 實作範圍

- Volatility：Wilder ATR14、ATR%、20 日對數報酬年化歷史波動、日內區間／ATR、開盤跳空及 252 日尾端 ATR% 百分位。
- 確定性 AVWAP：已確認波段低點、已確認波段高點、20 日突破日、20 日量比至少 1.8 的大量事件、絕對開盤跳空至少 2% 的事件。
- Location：已確認 pivot、MA20／60／120、AVWAP 與突破／跌破價位形成支撐／壓力匯聚區，並產生 Location 狀態。
- 未加入 M6 Evidence Vector 或 Market State。

## Point-in-time 與可稽核性

- Pivot AVWAP 同時保存 `anchor_date` 及 `confirmation_date`，只在 `market_date >= confirmation_date` 時產生。
- 突破、大量與跳空事件在當日資料可用後成為錨點，判定只讀取當日及更早資料。
- 正式資料庫檢查 1,337 筆 AVWAP，`confirmation_date > market_date` 違規筆數為 0。
- 每筆 AVWAP 保存公式推導、錨點價格及實際來源日期；每個 zone 保存 `level_types`、逐項價格、推導與來源日期。
- Zone 邊界依證交所股票價格跳動單位取整，不輸出無法交易的假精度。

## 正式資料驗收

3702 使用既有 304 筆官方 OHLCV，沒有新增資料 provider 或網路下載：

| 輸出 | 筆數 | 日期範圍 |
|---|---:|---|
| Volatility | 304 | 2025-07-01 至 2026-09-24 |
| Anchored VWAP | 1,337 | 2025-07-11 至 2026-09-24 |
| Location Zones | 545 | 2025-07-11 至 2026-09-24 |
| Location State | 304 | 2025-07-01 至 2026-09-24 |

AVWAP 類型筆數：突破日 201、已確認高點 289、已確認低點 296、跳空事件 287、大量事件 264。所有 545 個 zone 都具有 level types 與 derivations。V2 `analysis_snapshots` 保持 304 筆，最新日期仍為 2026-09-24。

3702 在 2026-09-24 的代表性結果：

- Volatility：`NORMAL`；ATR14 3.9293 元、ATR% 3.3441%、20 日年化歷史波動 26.4062%、尾端百分位 0.4722。
- 最新已確認低點 AVWAP：錨點 2026-08-31、確認日 2026-09-03、AVWAP 107.3553。
- 最新已確認高點 AVWAP：錨點 2026-09-10、確認日 2026-09-15、AVWAP 110.8628。
- 當日突破錨點 AVWAP：116.1667；最新大量事件 AVWAP：112.3028；最新跳空事件 AVWAP：111.3653。
- Location：`NEAR_SUPPORT`；支撐區 116.0、壓力區 122.0–123.0。支撐區由突破價位與突破日 AVWAP 匯聚，強度為 `MODERATE`。

## 測試與版本紀錄

- 完整測試：`93 passed in 10.37s`。
- 測試涵蓋 ATR／歷史波動、五種確定性錨點、AVWAP 手工公式核對、未來確認 pivot 隔離、zone 推導與跳動單位精度。
- `m5-volatility-location-v1` 的正式初驗只涵蓋已確認波段高低錨點；依不可變版本原則保留。補齊計畫明列的三種事件錨點後，以 v2 作為正式 M5 ruleset。

## 已知限制

- 行情仍是未還原權息價格；公司行動附近的 ATR、歷史波動與 AVWAP 需搭配既有 corporate-action 警告解讀。
- 波動百分位在累積至少 60 筆 ATR% 前保持資料不足；不補值。
- 門檻為可設定的描述性初版，將於 M9 進行 walk-forward 與參數穩健性檢查。波動狀態不提供方向性判斷。
