# 整合比較分析

## 用途

`generate_integrated_comparison.py` 會讀取三份已合併的 CSV，依三組廠商比較條件整合資料，產生評估明細與比較圖表。

## 輸入資料

程式預期輸入檔位於上一層 `01data merge` 目錄：

- `check_merged_09010930.csv`：計算 `suspect_count + anomaly_count` 的異常率。
- `status_merged_09010930.csv`：計算 `status_1_count + status_2_count` 的回傳數量。
- `comparison_merged_09010930_deduplicated.csv`：計算相對於 IISI01 的時間差。

三份 CSV 必須包含程式檢查的必要欄位；缺少欄位時會直接產生錯誤並停止。

## 執行方式

請在此資料夾執行：

```powershell
python generate_integrated_comparison.py
```

需要 Python 套件 `numpy` 與 `matplotlib`。若使用指定 Python 執行檔，請依 Windows PowerShell 語法在路徑前加 `&`。

## 評估規則

- 以 IISI01 的 `T` 格位作為基準，依比較組態對應對照廠商格位。
- 回傳數量一致度占 60%。
- 異常率品質占 25%；異常率越低分數越高，5% 以上為 0 分。
- 平均絕對時間差一致度占 15%；以 60 秒作為一致範圍。
- 時間差沒有資料時，會排除該項權重後重新正規化。
- 最終分數至少 90% 為「高評比」、至少 75% 為「中評比」，其餘為「低評比」。

## 輸出檔案

- `integrated_assessment.csv`：每個路段與格位的整合評估明細。

### 任務一：回傳數量比較

- `01_scatter_C01_T_vs_IISI01.png`
- `02_scatter_C01_NUM_vs_IISI01.png`
- `03_scatter_C03_vs_IISI01.png`

以上三張圖比較 IISI01 與各對照廠商的 STATUS1 + STATUS2 回傳數量一致性。

### 任務二：異常率比較

- `09_scatter_anomaly_C01_T_vs_IISI01.png`
- `10_scatter_anomaly_C01_NUM_vs_IISI01.png`
- `11_scatter_anomaly_C03_vs_IISI01.png`

以上三張圖比較兩家廠商的異常率一致性，顏色代表對照廠商異常率。

### 任務三：最終評比

- `05_final_metric_scores.png`：各項指標平均分數。
- `06_final_vendor_scores.png`：廠商最終分數柱狀圖。
- `07_final_vendor_scores_line.png`：廠商最終分數折線圖。
- `08_final_vendor_scores_scatter.png`：兩家廠商最終分數散點圖。

以上四張圖從指標、分數高低、變化趨勢與兩家廠商關係，呈現綜合評比結果。

## 注意事項

程式會覆寫同名輸出檔案。`save_bland_altman`、`save_difference_ranking` 與 `save_assessment_heatmap` 已保留為獨立輸出函式，但目前 `main()` 未呼叫它們；如需產生這三類圖表，需在主流程中明確加入呼叫。