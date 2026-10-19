from datetime import date

from config import (
    DAILY_STATISTICS_TABLE,
    SIGNALS,
    SOURCE_SIGNAL_COLUMN,
    SOURCE_TABLE,
    SOURCE_TIME_COLUMN,
)
from database import column_exists, table_exists


def ensure_statistics_table(connection: object) -> None:
    # 區塊：保留舊版廠商彙總表，避免其主鍵與逐格統計衝突
    if table_exists(connection, DAILY_STATISTICS_TABLE):
        if column_exists(connection, DAILY_STATISTICS_TABLE, "section_id") and column_exists(
            connection, DAILY_STATISTICS_TABLE, "ps_id"
        ):
            return
        backup_table = f"{DAILY_STATISTICS_TABLE}_vendor_backup"
        if table_exists(connection, backup_table):
            raise RuntimeError(f"Backup table already exists: {backup_table}")
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"ALTER TABLE {DAILY_STATISTICS_TABLE} "
                f"RENAME TO {backup_table.rsplit('.', 1)[-1]}"
            )
        finally:
            cursor.close()

    # 區塊：建立每天、廠商、路段及格位的統計結果表
    sql = f"""
    CREATE TABLE {DAILY_STATISTICS_TABLE} (
        statistics_date DATE NOT NULL,
        vendorcode VARCHAR(50) NOT NULL,
        section_id VARCHAR(100) NOT NULL,
        ps_id VARCHAR(100) NOT NULL,
        status_1_count INT NOT NULL,
        status_2_count INT NOT NULL,
        total_count INT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        PRIMARY KEY (statistics_date, vendorcode, section_id, ps_id)
    )
    """
    cursor = connection.cursor()
    try:
        cursor.execute(sql)
    finally:
        cursor.close()


def clear_statistics_by_date(connection: object, analysis_date: date) -> None:
    # 區塊：重跑前先刪除同日期舊資料
    sql = f"DELETE FROM {DAILY_STATISTICS_TABLE} WHERE statistics_date = %s"
    cursor = connection.cursor()
    try:
        cursor.execute(sql, (analysis_date,))
    finally:
        cursor.close()


def run_daily_statistics(connection: object, analysis_date: date) -> int:
    # 區塊：逐日、逐廠商及逐格統計 status=1/2 與總筆數
    status_1, status_2 = SIGNALS
    source_time_expr = f"CAST({SOURCE_TIME_COLUMN} AS TIMESTAMP)"
    sql = f"""
    INSERT INTO {DAILY_STATISTICS_TABLE} (
        statistics_date,
        vendorcode,
        section_id,
        ps_id,
        status_1_count,
        status_2_count,
        total_count,
        created_at
    )
    SELECT
        %s AS statistics_date,
        vendorcode,
        section_id,
        ps_id,
        SUM(CASE WHEN {SOURCE_SIGNAL_COLUMN} = %s THEN 1 ELSE 0 END) AS status_1_count,
        SUM(CASE WHEN {SOURCE_SIGNAL_COLUMN} = %s THEN 1 ELSE 0 END) AS status_2_count,
        SUM(CASE WHEN {SOURCE_SIGNAL_COLUMN} IN (%s, %s) THEN 1 ELSE 0 END) AS total_count,
        CURRENT_TIMESTAMP AS created_at
    FROM {SOURCE_TABLE}
    WHERE DATE({source_time_expr}) = %s
    GROUP BY vendorcode, section_id, ps_id
    """
    cursor = connection.cursor()
    try:
        cursor.execute(
            sql,
            (analysis_date, status_1, status_2, status_1, status_2, analysis_date),
        )
    finally:
        cursor.close()

    # 區塊：查詢實際寫入筆數，避免資料庫 rowcount 回傳負值
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"SELECT COUNT(*) FROM {DAILY_STATISTICS_TABLE} "
            "WHERE statistics_date = %s",
            (analysis_date,),
        )
        return int(cursor.fetchone()[0])
    finally:
        cursor.close()