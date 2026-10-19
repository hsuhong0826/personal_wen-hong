# check09010930 分析圖表

## 用途

`analyze_check.py` 讀取上一層的 `check_merged_09010930.csv`，依路段、廠商與 `ps_id` 彙總三種數量，計算整體異常率並產生廠商比較圖。

原始 CSV 不會被修改；圖表與摘要 CSV 會輸出在本資料夾。

## 分析分組

- `3148038`、`3148040`：比較 IISI01_T 與 C01_T。
- `3148038`、`3148040`：比較 IISI01_T 與對應的 C01 數字格位。
- `2098000`：比較 IISI01_T 與對應的 C03 數字格位。

整體摘要圖使用相同路段與對應格位口徑，避免將不同範圍的分母直接混合比較。數字格位比較是依 `IISI01_T` 去除 `T` 前綴後，對應目標廠商的數字格位。

整體異常率定義為：

```text
(suspect_count + anomaly_count) / total_count
```

總數為 0 時，異常率計為 0%。

## 輸入格式

預設輸入檔案：`..\check_merged_09010930.csv`

必要欄位：

```text
vendorcode
section_id
ps_id
total_count
suspect_count
anomaly_count
```

缺少必要欄位時，程式會顯示錯誤並停止。空白數量視為 0。

## 執行方式

在工作區根目錄執行：

```powershell
python ".\01data merge\check09010930\analyze_check.py"
```

也可以指定其他來源 CSV：

```powershell
python ".\01data merge\check09010930\analyze_check.py" ".\01data merge\check_merged_09010930.csv"
```

需要安裝 `matplotlib`。

## 輸出檔案

- `01_IISI01_T_to_C01_T_line_v2.png`：IISI01_T 與 C01_T 格位比較。
- `02_IISI01_T_to_C01_numeric_line_v2.png`：IISI01_T 與 C01 數字格位比較。
- `03_IISI01_T_to_C03_numeric.png`：IISI01_T 與 C03 數字格位比較。
- `04_2098000_IISI01_T_to_C03_numeric_line.png`：2098000 的折線比較。
- `03_overall_rate_summary_line_v2.png`：三組公平配對的整體異常率折線圖。
- `05_overall_rate_summary_bar.png`：三組公平配對的整體異常率長條圖。
- `03_overall_summary.csv`：各路段／廠商的彙總數量與異常率。

摘要圖中的百分比標註會依資料點左右錯開；最左側與最右側標註會移入圖框，避免文字超出邊界。

## 可選任務分工

1. 資料讀取與欄位檢查：`read_data()`。
2. 異常率計算與數量彙總：`rate()`、`add_row()`、`combine_totals()`。
3. 圖表產生：各 `save_*_chart()` 函式。
4. 執行入口與參數處理：`main()`。