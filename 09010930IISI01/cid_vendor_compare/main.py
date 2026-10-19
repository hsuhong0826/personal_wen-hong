import time

from logger import get_logger
from comparison import (
    clear_existing_results,
    ensure_comparison_table,
    get_analysis_date,
    run_comparison,
)
from config import get_forced_analysis_date, settings
from database import get_connection
from daily_statistics import (
    clear_statistics_by_date,
    ensure_statistics_table,
    run_daily_statistics,
)


logger = get_logger()


def main() -> None:
    # 區塊：記錄主流程啟動與總耗時
    process_started_at = time.perf_counter()

    # 區塊：決定分析日期（有強制日期優先，否則取昨天）
    analysis_date = get_forced_analysis_date() or get_analysis_date()
    logger.info("開始環境檢查")

    # 區塊：兩個任務分開記錄成功狀態，互不影響
    task_1_ok = False
    task_2_ok = False
    try:
        with get_connection() as connection:
            logger.info("環境檢查完成")
            logger.info("開始處理日期: %s", analysis_date)
            logger.info("%s 狀態 RUNNING", analysis_date)

            # 區塊：Task 1 每日廠商狀態筆數統計
            try:
                ensure_statistics_table(connection)
                clear_statistics_by_date(connection, analysis_date)
                stats_count = run_daily_statistics(connection, analysis_date)
                # 區塊：測試模式不落地，正式模式提交交易
                if settings.dry_run:
                    connection.rollback()
                else:
                    connection.commit()
                task_1_ok = True
            except Exception:
                connection.rollback()
                logger.exception("每日統計任務失敗: %s", analysis_date)

            # 區塊：Task 2 三方橫向比對
            try:
                ensure_comparison_table(connection)
                clear_existing_results(connection, analysis_date)
                compare_count = run_comparison(connection, analysis_date)
                # 區塊：測試模式不落地，正式模式提交交易
                if settings.dry_run:
                    connection.rollback()
                else:
                    connection.commit()
                task_2_ok = True
            except Exception:
                connection.rollback()
                logger.exception("橫向比對任務失敗: %s", analysis_date)
    except Exception:
        # 區塊：連線層級失敗
        logger.exception("資料庫連線失敗: %s", analysis_date)
        raise

    # 區塊：任一任務失敗時回傳失敗狀態
    if not (task_1_ok and task_2_ok):
        elapsed_seconds = time.perf_counter() - process_started_at
        logger.error("%s 狀態 FAILED，耗時 %.1f 秒", analysis_date, elapsed_seconds)
        logger.info(
            "主流程完成，成功 %s 天，失敗 %s 天，總耗時 %.1f 分鐘",
            int(task_1_ok and task_2_ok),
            int(not (task_1_ok and task_2_ok)),
            elapsed_seconds / 60,
        )
        raise RuntimeError("One or more tasks failed. Check logs for details.")

    # 區塊：記錄單日成功結果與主流程摘要
    elapsed_seconds = time.perf_counter() - process_started_at
    logger.info(
        "%s 狀態 SUCCESS，統計格位 %s 筆、比對結果 %s 筆，耗時 %.1f 秒",
        analysis_date,
        stats_count,
        compare_count,
        elapsed_seconds,
    )
    logger.info(
        "主流程完成，成功 1 天，失敗 0 天，總耗時 %.1f 分鐘",
        elapsed_seconds / 60,
    )


if __name__ == "__main__":
    main()
