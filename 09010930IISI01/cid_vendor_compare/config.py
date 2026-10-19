import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# 區塊：讀取環境設定檔
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    ENV_FILE = BASE_DIR / ".env"
    if not ENV_FILE.exists():
        ENV_FILE = Path(__file__).resolve().parent / ".env"
else:
    BASE_DIR = Path(__file__).resolve().parent
    ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)


@dataclass(frozen=True)
class Settings:
    # 區塊：Vertica 連線設定（相容 VERTICA_* 與 DB_* 命名）
    vertica_host: str = os.getenv("VERTICA_HOST") or os.getenv("DB_HOST", "")
    vertica_port: int = int(os.getenv("VERTICA_PORT") or os.getenv("DB_PORT", "5433"))
    vertica_database: str = os.getenv("VERTICA_DATABASE") or os.getenv("DB_NAME", "")
    vertica_user: str = os.getenv("VERTICA_USER") or os.getenv("DB_USER", "")
    vertica_password: str = os.getenv("VERTICA_PASSWORD") or os.getenv("DB_PASSWORD", "")
    vertica_schema: str = os.getenv("VERTICA_SCHEMA") or os.getenv("SOURCE_SCHEMA", "")

    # 區塊：來源與目標資料表設定
    source_schema: str = os.getenv("SOURCE_SCHEMA", "")
    source_table: str = os.getenv("SOURCE_TABLE", "roadsection")
    target_schema: str = os.getenv("TARGET_SCHEMA", "")

    # 區塊：執行控制參數
    dry_run: bool = (os.getenv("DRY_RUN", "false").strip().lower() == "true")
    force_analysis_date: str = os.getenv("FORCE_ANALYSIS_DATE", "").strip()
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


def _qualified_table(schema: str, table: str) -> str:
    # 區塊：依 schema 組合完整資料表名稱
    return f"{schema}.{table}" if schema else table


# 區塊：系統常數與預設配置
settings = Settings()

SOURCE_TABLE = _qualified_table(settings.source_schema, settings.source_table)
DAILY_STATISTICS_TABLE = _qualified_table(
    settings.target_schema,
    "cid_daily_vendor_count_statistics",
)
COMPARISON_RESULTS_TABLE = _qualified_table(
    settings.target_schema,
    "cid_three_vendor_comparison_results",
)
_vendors_env = os.getenv("VENDORS", "IISI01,C01,C03")
VENDORS = tuple(v.strip() for v in _vendors_env.split(",") if v.strip())
# 區塊：比對 VENDORS 設定中的所有格位
SIGNALS = (1, 2)
SOURCE_TIME_COLUMN = os.getenv("SOURCE_TIME_COLUMN", "sta_dt")
SOURCE_SIGNAL_COLUMN = os.getenv("SOURCE_SIGNAL_COLUMN", "status")


def get_forced_analysis_date() -> date | None:
    # 區塊：若有指定強制分析日期，優先使用該日期
    if not settings.force_analysis_date:
        return None
    return date.fromisoformat(settings.force_analysis_date)
