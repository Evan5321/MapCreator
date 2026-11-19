"""唯一的数据库访问入口（facade）。

实现拆分在 `core`（连接/schema）、`store`（CRUD/搜索）、`dump`（导入导出）；
**调用方只 import 本模块**，不直接依赖 `core`/`store`/`dump`。

规则（AGENTS.md 规则 1、docs/DATA_SPEC.md §5）：
- 所有写入使用参数化 SQL + 单事务；
- `search_text` 在同一事务内由本层重算；
- `revision` 每次写入 +1；软删除用 `deleted_at`；
- 不绕过触发器直接删 FTS/RTree 行。
"""

from .core import (
    JOURNAL_MODES,
    SCHEMA_SQL,
    SCHEMA_VERSION,
    connect,
    get_meta,
    init_schema,
    schema_version,
)
from .dump import check_search_text, dump_sql, rebuild_indexes, restore_sql, verify_dump
from .store import (
    all_annotations,
    export_annotations,
    get_annotation,
    names_for,
    recompute_search_text,
    restore,
    search,
    search_text_for,
    soft_delete,
    upsert_annotation,
)

__all__ = [
    "JOURNAL_MODES",
    "SCHEMA_SQL",
    "SCHEMA_VERSION",
    "all_annotations",
    "check_search_text",
    "connect",
    "dump_sql",
    "export_annotations",
    "get_annotation",
    "get_meta",
    "init_schema",
    "names_for",
    "rebuild_indexes",
    "recompute_search_text",
    "restore",
    "restore_sql",
    "schema_version",
    "search",
    "search_text_for",
    "soft_delete",
    "upsert_annotation",
    "verify_dump",
]
