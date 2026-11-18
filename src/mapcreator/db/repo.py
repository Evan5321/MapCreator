"""标注 / 名称 / 关系仓库：唯一的数据库写入口。

规则（AGENTS.md 规则 1、docs/DATA_SPEC.md §5）：
- 所有写入使用参数化 SQL + 单事务；
- `search_text` 在同一事务内由本层重算；
- `revision` 每次写入 +1；软删除用 `deleted_at`；
- 不绕过触发器直接删表行。

骨架阶段：签名固定，实现见 TASK-0004。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from ..models import Annotation

TASK = "TASK-0004"


def connect(db_path: Path) -> sqlite3.Connection:
    """打开连接：WAL、foreign_keys=ON、busy_timeout。"""
    raise NotImplementedError(TASK)


def init_schema(conn: sqlite3.Connection, schema_sql: Path) -> None:
    """执行 schema.sql（幂等）并写入 meta.schema_version。"""
    raise NotImplementedError(TASK)


def get_annotation(conn: sqlite3.Connection, annotation_id: str) -> Annotation | None:
    """按 ID 取详情（含全部名称）；已软删除视为不存在。"""
    raise NotImplementedError(TASK)


def search(
    conn: sqlite3.Connection,
    query: str,
    *,
    lang: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """>=3 字符走 FTS5 trigram，1-2 字符回退 LIKE（D-017）。"""
    raise NotImplementedError(TASK)


def upsert_annotation(conn: sqlite3.Connection, annotation: Annotation) -> Annotation:
    """插入或更新；旧 revision 冲突时抛 DataValidationError(REVISION_CONFLICT)。"""
    raise NotImplementedError(TASK)


def soft_delete(conn: sqlite3.Connection, annotation_id: str, *, revision: int) -> None:
    """软删除（deleted_at 置值），不物理删除。"""
    raise NotImplementedError(TASK)


def restore(conn: sqlite3.Connection, annotation_id: str) -> None:
    """恢复软删除的标注。"""
    raise NotImplementedError(TASK)


def recompute_search_text(conn: sqlite3.Connection, annotation_id: str) -> str:
    """名称（全语种 + 别名）+ description，空格连接。"""
    raise NotImplementedError(TASK)


def dump_sql(conn: sqlite3.Connection, out: Path) -> None:
    """只导逻辑表，稳定排序（meta/annotation/annotation_name/relation/relation_member）。"""
    raise NotImplementedError(TASK)


def restore_sql(conn: sqlite3.Connection, src: Path) -> None:
    """导入逻辑表后重建 FTS/RTree。"""
    raise NotImplementedError(TASK)


def verify_dump(conn: sqlite3.Connection, src: Path) -> list[str]:
    """返回不一致项清单（空 = 一致），含 search_text 校验。"""
    raise NotImplementedError(TASK)
