"""数据库连接与 schema 初始化（repo 的实现拆分）。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..errors import DataValidationError

SCHEMA_VERSION = 1
SCHEMA_SQL = Path(__file__).with_name("schema.sql")
JOURNAL_MODES = frozenset({"WAL", "DELETE", "TRUNCATE", "PERSIST", "MEMORY", "OFF"})


def connect(db_path: Path, *, journal_mode: str = "WAL") -> sqlite3.Connection:
    """打开连接：foreign_keys=ON、busy_timeout=5s、指定 journal_mode。"""
    mode = journal_mode.upper()
    if mode not in JOURNAL_MODES:
        raise DataValidationError(
            code="JOURNAL_MODE_INVALID",
            message=f"不支持的 journal_mode：{journal_mode!r}",
            remediation=f"可选：{sorted(JOURNAL_MODES)}",
        )
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute(f"PRAGMA journal_mode = {mode}")
    return conn


def init_schema(
    conn: sqlite3.Connection,
    schema_sql: Path = SCHEMA_SQL,
    *,
    world_id: str = "",
    default_lang: str = "zh",
) -> None:
    """执行 schema.sql（幂等）并补齐 meta 默认值。"""
    conn.executescript(schema_sql.read_text(encoding="utf-8"))
    conn.executemany(
        "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO NOTHING",
        [
            ("schema_version", str(SCHEMA_VERSION)),
            ("world_id", world_id),
            ("default_lang", default_lang),
        ],
    )
    conn.commit()


def schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    return int(row["value"]) if row is not None else 0


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row is not None else None
