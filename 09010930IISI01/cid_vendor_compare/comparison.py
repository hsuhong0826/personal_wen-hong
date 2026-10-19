from datetime import date, datetime, timedelta
from config import (
    COMPARISON_RESULTS_TABLE,
    SOURCE_SIGNAL_COLUMN,
    SOURCE_TABLE,
    SOURCE_TIME_COLUMN,
    VENDORS,
)
from database import column_exists, table_exists


def get_analysis_date(run_time: datetime | None = None) -> date:
    # 區塊：預設分析日期為執行日的昨天
    run_time = run_time or datetime.now()
    return (run_time - timedelta(days=1)).date()


def ensure_comparison_table(connection: object) -> None:
    # 區塊：Task 2 比對結果表，不存在時自動建立
    table_already_exists = table_exists(connection, COMPARISON_RESULTS_TABLE)
    sql = f"""
    CREATE TABLE {COMPARISON_RESULTS_TABLE} (
        comparison_date DATE NOT NULL,
        baseline_vendor VARCHAR(50) NOT NULL,
        section_id VARCHAR(100) NOT NULL,
        ps_id VARCHAR(100) NOT NULL,
        status INT NOT NULL,
        baseline_time TIMESTAMP NOT NULL,
        target_vendor VARCHAR(50) NOT NULL,
        target_ps_id VARCHAR(100),
        matched_time TIMESTAMP,
        time_difference_seconds INT,
        difference_rate NUMERIC(12, 8),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    if not table_already_exists:
        cursor = connection.cursor()
        try:
            cursor.execute(sql)
        finally:
            cursor.close()

    # 區塊：既有結果表補上目標廠商的地磁 ID 欄位
    if column_exists(connection, COMPARISON_RESULTS_TABLE, "target_ps_id"):
        return

    cursor = connection.cursor()
    try:
        cursor.execute(
            f"ALTER TABLE {COMPARISON_RESULTS_TABLE} "
            "ADD COLUMN target_ps_id VARCHAR(100)"
        )
    finally:
        cursor.close()


def clear_existing_results(connection: object, analysis_date: date) -> None:
    # 區塊：重跑前先刪除同日期舊資料
    sql = f"DELETE FROM {COMPARISON_RESULTS_TABLE} WHERE comparison_date = %s"
    cursor = connection.cursor()
    try:
        cursor.execute(sql, (analysis_date,))
    finally:
        cursor.close()


def _insert_vendor_direction(
    connection: object,
    analysis_date: date,
    source_vendor: str,
    target_vendor: str,
) -> int:
    # 區塊：單一方向比對兩家廠商的所有格位
    # 規則：同路段/格位/訊號，取最小時間差；等距全部保留；找不到寫未配對
    source_time_expr = f"CAST({SOURCE_TIME_COLUMN} AS TIMESTAMP)"
    sql = f"""
    INSERT INTO {COMPARISON_RESULTS_TABLE} (
        comparison_date,
        baseline_vendor,
        section_id,
        ps_id,
        status,
        baseline_time,
        target_vendor,
        target_ps_id,
        matched_time,
        time_difference_seconds,
        difference_rate,
        created_at
    )
    WITH source_rows AS (
        SELECT
                        ROW_NUMBER() OVER (ORDER BY section_id, ps_id, {SOURCE_SIGNAL_COLUMN}, {source_time_expr}) AS src_row_id,
            section_id,
            ps_id,
                CASE WHEN ps_id LIKE 'T%%' THEN SUBSTR(ps_id, 2) ELSE ps_id END AS ps_key,
            {SOURCE_SIGNAL_COLUMN} AS status,
                        {source_time_expr} AS source_time
        FROM {SOURCE_TABLE}
        WHERE vendorcode = %s
                    AND DATE({source_time_expr}) = %s
                    -- 區塊：僅保留來源表 status = 1 或 2 的資料
                    AND {SOURCE_SIGNAL_COLUMN} IN (1, 2)
    ),
    target_rows AS (
        SELECT
            section_id,
            ps_id,
                CASE WHEN ps_id LIKE 'T%%' THEN SUBSTR(ps_id, 2) ELSE ps_id END AS ps_key,
            {SOURCE_SIGNAL_COLUMN} AS status,
                        {source_time_expr} AS target_time
        FROM {SOURCE_TABLE}
        WHERE vendorcode = %s
                    AND DATE({source_time_expr}) = %s
                    -- 區塊：比對對象同樣僅使用 status = 1 或 2
                    AND {SOURCE_SIGNAL_COLUMN} IN (1, 2)
    ),
    candidates AS (
        SELECT
            s.src_row_id,
            s.section_id,
            s.ps_id,
            s.status,
            s.source_time,
                t.ps_id AS target_ps_id,
            t.target_time,
            DATEDIFF('second', s.source_time, t.target_time) AS signed_diff_seconds,
            ABS(DATEDIFF('second', s.source_time, t.target_time)) AS diff_seconds
        FROM source_rows s
        LEFT JOIN target_rows t
          ON s.section_id = t.section_id
            AND s.ps_key = t.ps_key
         AND s.status = t.status
    ),
    min_diff AS (
        SELECT
            src_row_id,
            MIN(diff_seconds) AS min_diff
        FROM candidates
        WHERE diff_seconds IS NOT NULL
        GROUP BY src_row_id
    )
    SELECT
        %s AS comparison_date,
        %s AS baseline_vendor,
        c.section_id,
        c.ps_id,
        c.status,
        c.source_time AS baseline_time,
        %s AS target_vendor,
        c.target_ps_id,
        c.target_time AS matched_time,
        -- 區塊：以絕對值選最近配對，輸出時保留目標相對基準的正負方向
        c.signed_diff_seconds AS time_difference_seconds,
        CASE
            WHEN c.signed_diff_seconds IS NULL THEN NULL
            ELSE ROUND((c.signed_diff_seconds / 86400.0) * 100, 8)
        END AS difference_rate,
        CURRENT_TIMESTAMP AS created_at
    FROM candidates c
    LEFT JOIN min_diff m
      ON c.src_row_id = m.src_row_id
    WHERE (m.min_diff IS NULL AND c.target_time IS NULL)
       OR c.diff_seconds = m.min_diff
    """
    cursor = connection.cursor()
    try:
        cursor.execute(
            sql,
            (
                source_vendor,
                analysis_date,
                target_vendor,
                analysis_date,
                analysis_date,
                source_vendor,
                target_vendor,
            ),
        )
        return cursor.rowcount or 0
    finally:
        cursor.close()


def run_comparison(connection: object, analysis_date: date) -> int:
    """Task 2：以第一家廠商為中心，與其餘廠商逐一雙向比對所有格位。

    規則：
    - 廠商由 VENDORS 設定提供。
    - 格位比對時忽略開頭的 T，結果保留實際 ps_id。
    - 相同 section_id、格位、signal。
    - 僅處理 status 1、2。
    - 取時間差最小。
    - 時間差相同全部保留。
    - 允許重複配對。
    - 找不到時寫入未配對。
    """
    # 區塊：中心廠商與其餘廠商雙向比對，不比對其餘廠商彼此
    for other_vendor in VENDORS[1:]:
        for source_vendor, target_vendor in ((VENDORS[0], other_vendor), (other_vendor, VENDORS[0])):
            _insert_vendor_direction(
                connection,
                analysis_date,
                source_vendor,
                target_vendor,
            )

    # 區塊：查詢實際寫入筆數，避免資料庫 rowcount 回傳負值
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"SELECT COUNT(*) FROM {COMPARISON_RESULTS_TABLE} "
            "WHERE comparison_date = %s",
            (analysis_date,),
        )
        return int(cursor.fetchone()[0])
    finally:
        cursor.close()
