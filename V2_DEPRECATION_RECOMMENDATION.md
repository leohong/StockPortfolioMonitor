# V2 Deprecation Recommendation

日期：2026-09-26  
建議：**保留 V2，不標記 deprecated，不移除資料、程式或介面。**

## 判斷

| 移除條件 | 狀態 | 證據 |
|---|---|---|
| V3 snapshots stable | 通過 | 304 日 replay 完全一致；version identity immutable |
| Regression suite passes | 通過 | M9 完整測試通過 |
| Historical replay passes | 通過 | 0 mismatch、0 future-source violation |
| UI/export parity | 通過 | M8 已驗證 V3 預設與 V2 歷史／匯出並存 |
| User accepted V3 workflow | 尚無充分觀察期證據 | 已要求並完成 M8/M9，但尚未累積實際使用觀察期與明確淘汰決定 |

即使多數技術條件已通過，目前仍只有一檔正式持股、304 個交易日，walk-forward 結果也不支持將 V3 視為預測工具。保留 V2 可提供歷史稽核基準與回退路徑，成本低於現在移除它的風險。

## 重新評估條件

只有在下列條件都有可查證紀錄後，才建議另開獨立工作評估 V2 removal：

1. 使用者明確接受 V3 工作流程並要求進入淘汰評估。
2. V3 在更長觀察期與多檔正式持股上維持 snapshot 穩定與 UI/export parity。
3. 完整 regression、point-in-time replay 與 migration backup/restore 演練持續通過。
4. 先建立唯讀封存與還原方案，再分開處理 UI 隱藏、寫入停止、程式移除與資料表移除。

本文件不是移除授權。任何 V2 schema、資料或程式刪除都必須是後續獨立、明確授權且可回復的 migration。
