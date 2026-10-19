# CID 地磁廠商比對程式

每日讀取來源資料，執行兩個獨立任務：

- Task 1：統計各廠商的 `status=1`、`status=2` 與總筆數。
- Task 2：依格位與狀態比對廠商資料，計算時間差。

預設分析日期為昨天，也可用 `FORCE_ANALYSIS_DATE` 指定日期。

## 各程式的工作

- `main.py`：程式入口。決定分析日期，依序執行兩個任務，處理資料庫交易與成功/失敗紀錄。
- `config.py`：讀取 `.env`，集中管理資料庫、資料表、廠商與執行參數。
- `database.py`：建立 Vertica 連線，並提供共用的 SQL、資料表與欄位檢查功能。
- `daily_statistics.py`：實作 Task 1。建立統計表、清除指定日期舊資料，寫入各廠商的每日筆數。
- `comparison.py`：實作 Task 2。建立比對表、清除指定日期舊資料，依 `section_id`、格位與 `status` 比對廠商資料，保留最小時間差。
- `logger.py`：建立共用日誌，同時輸出到主控台與 `logs` 目錄。

## 任務結果表

- `cid_daily_vendor_count_statistics`：Task 1 的每日統計結果。
- `cid_three_vendor_comparison_results`：Task 2 的廠商比對結果。

若設定 `TARGET_SCHEMA`，結果表會建立在指定 schema。

## 執行方式

```powershell
pip install -r requirements.txt
python main.py
```

## 主要設定

請在 `.env` 設定：

- `DB_HOST`、`DB_PORT`、`DB_NAME`、`DB_USER`、`DB_PASSWORD`：資料庫連線資訊。
- `SOURCE_SCHEMA`、`SOURCE_TABLE`：來源資料表。
- `TARGET_SCHEMA`：結果表 schema，可選填。
- `VENDORS`：要比對的廠商，第一家為中心廠商，預設為 `IISI01,C01,C03`。
- `FORCE_ANALYSIS_DATE`：指定分析日期，格式為 `YYYY-MM-DD`，可選填。
- `DRY_RUN`：設為 `true` 時執行後回復交易，不寫入正式資料。

## 注意事項

- Task 2 以 `IISI01` 為中心，與 `C01`、`C03` 各做雙向比對（共四個方向）；不比對 `C01` 與 `C03`。
- 比對只處理來源資料中 `status=1` 或 `status=2` 的紀錄。
- 比對條件為相同 `section_id`、格位與 `status`，並保留時間差最小的配對；時間差相同時會全部保留。
- 找不到對應資料時仍會寫入結果，`matched_time` 與時間差會是空值。
- 重新執行相同分析日期時，會先刪除該日期的舊結果，再重新寫入。
- 正式執行前建議先設定 `DRY_RUN=true` 確認流程與筆數；確認無誤後再改為 `false`。
- 執行環境必須能連線 Vertica，且 `.env` 的資料庫連線資訊與來源資料表設定須正確。

程式會在每次執行前清除同一分析日期的舊結果，再重新寫入；執行紀錄會保留在 `logs` 目錄。
