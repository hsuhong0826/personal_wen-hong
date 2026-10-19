from contextlib import contextmanager
from typing import Iterator

from config import settings

# 區塊：延後載入資料庫套件，避免未安裝時模組直接失敗
try:
    import vertica_python
except ImportError:  # Allows the project to be inspected before dependencies are installed.
    vertica_python = None


@contextmanager
def get_connection() -> Iterator[object]:
    # 區塊：建立並回傳 Vertica 連線
    if vertica_python is None:
        raise RuntimeError("vertica-python is not installed")

    connection = vertica_python.connect(
        host=settings.vertica_host,
        port=settings.vertica_port,
        database=settings.vertica_database,
        user=settings.vertica_user,
        password=settings.vertica_password,
        search_path=settings.vertica_schema,
        tlsmode="disable",
    )
    try:
        yield connection
    finally:
        connection.close()


def execute(connection: object, sql: str, parameters: tuple = ()) -> None:
    # 區塊：共用 SQL 執行函式
    cursor = connection.cursor()
    try:
        cursor.execute(sql, parameters)
    finally:
        cursor.close()


def table_exists(connection: object, table_name: str) -> bool:
    # 區塊：查詢結果表是否已存在，避免 Vertica 產生 IF NOT EXISTS NOTICE
    schema_name, short_table_name = _split_table_name(table_name)
    schema_name = _resolve_schema(connection, schema_name)
    sql = (
        "SELECT 1 FROM v_catalog.tables "
        "WHERE table_schema = %s "
        "AND table_name = %s LIMIT 1"
    )
    cursor = connection.cursor()
    try:
        cursor.execute(sql, (schema_name, short_table_name))
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def column_exists(connection: object, table_name: str, column_name: str) -> bool:
    # 區塊：查詢結果表欄位是否已存在，避免重複 ADD COLUMN NOTICE
    schema_name, short_table_name = _split_table_name(table_name)
    schema_name = _resolve_schema(connection, schema_name)
    sql = (
        "SELECT 1 FROM v_catalog.columns "
        "WHERE table_schema = %s "
        "AND table_name = %s AND column_name = %s LIMIT 1"
    )
    cursor = connection.cursor()
    try:
        cursor.execute(sql, (schema_name, short_table_name, column_name))
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def _split_table_name(table_name: str) -> tuple[str | None, str]:
    # 區塊：拆分 schema.table；未指定 schema 時交由 Vertica 使用目前 schema
    parts = table_name.split(".", 1)
    if len(parts) == 1:
        return None, parts[0]
    return parts[0], parts[1]


def _resolve_schema(connection: object, schema_name: str | None) -> str:
    if schema_name is not None:
        return schema_name

    cursor = connection.cursor()
    try:
        cursor.execute("SELECT CURRENT_SCHEMA()")
        result = cursor.fetchone()
        if result is None or result[0] is None:
            raise RuntimeError("Unable to determine the current Vertica schema")
        return result[0]
    finally:
        cursor.close()
