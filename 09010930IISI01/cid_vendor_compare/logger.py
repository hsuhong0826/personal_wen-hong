import logging
from datetime import date
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import BASE_DIR, settings


def get_logger(name: str = "magnetic_compare") -> logging.Logger:
    # 區塊：建立共用 logger，避免重複掛載 handler
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    # 區塊：設定輸出層級與 logs 目錄
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)

    # 區塊：統一日誌格式，時間包含毫秒並標示層級
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # 區塊：檔案輸出（每日一檔）
    daily_log_name = f"analysis_{date.today():%Y%m%d}"
    file_handler = RotatingFileHandler(
        log_dir / daily_log_name,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 區塊：同步輸出到主控台
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger
