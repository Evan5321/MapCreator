"""逻辑表 dump / restore / verify-dump（repo 的实现拆分）。

只导 meta / annotation / annotation_name / relation / relation_member；
FTS/RTree 是派生索引，restore 后由 rebuild_indexes 重建。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .core import SCHEMA_SQL, init_schema, schema_version
from .store import names_for, search_text_for

LOGICAL_TABLES = ("meta", "annotation", "annotation_name", "relation", "relation_member")
ORDER_BY = {
    "meta": "key",
    "annotation": "fid",
    "annotation_name": "annotation_id, lang, name, role",
    "relation": "id",
    "relation_member": "relation_id, seq, member_id, role",
}


def dump_sql(conn: sqlite3.Connection, out: Path) -> None:
    """把逻辑表写成稳定、可读、可重放的 SQL。"""
    lines = [
        "-- MapCreator annotations dump：只含逻辑表；FTS/RTree 由 db restore 重建。",
        f"-- schema_version: {schema_version(conn)}",
        "BEGIN TRANSACTION;",
    ]
    for table in reversed(LOGICAL_TABLES):
        lines.append(f"DELETE FROM {table};")
    for table in LOGICAL_TABLES:
        columns = _columns(conn, table)
        column_sql = ", ".join(columns)
        rows = conn.execute(f"SELECT {column_sql} FROM {table} ORDER BY {ORDER_BY[table]}")
        for row in rows:
            values = ", ".join(_literal(row[column]) for column in columns)
            lines.append(f"INSERT INTO {table}({column_sql}) VALUES({values});")
    lines.append("COMMIT;")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def restore_sql(conn: sqlite3.Connection, src: Path) -> None:
    """导入逻辑表后重建 FTS/RTree。"""
    conn.executescript(src.read_text(encoding="utf-8"))
    rebuild_indexes(conn)


def rebuild_indexes(conn: sqlite3.Connection) -> None:
    """从 annotation 重建 FTS 与 RTree（dump 不含派生索引）。"""
    conn.execute("INSERT INTO annotation_fts(annotation_fts) VALUES('rebuild')")
    conn.execute("DELETE FROM annotation_rtree")
    conn.execute(
        """INSERT INTO annotation_rtree(fid, min_lon, max_lon, min_lat, max_lat)
           SELECT fid, lon, lon, lat, lat FROM annotation"""
    )
    conn.commit()


def verify_dump(conn: sqlite3.Connection, src: Path) -> list[str]:
    """返回不一致项清单（空 = 一致），含行数与 search_text 校验。"""
    problems: list[str] = []
    dump_conn = sqlite3.connect(":memory:")
    dump_conn.row_factory = sqlite3.Row
    try:
        init_schema(dump_conn)
        dump_conn.executescript(src.read_text(encoding="utf-8"))
        rebuild_indexes(dump_conn)

        live_version = schema_version(conn)
        dump_version = schema_version(dump_conn)
        if live_version != dump_version:
            problems.append(
                f"meta: schema_version 不一致（工作库 {live_version}，dump {dump_version}）"
            )

        for table in LOGICAL_TABLES:
            columns = _columns(conn, table)
            live_rows = _rows(conn, table, columns)
            dump_rows = _rows(dump_conn, table, columns)
            if len(live_rows) != len(dump_rows):
                problems.append(
                    f"{table}: 行数不一致（工作库 {len(live_rows)}，dump {len(dump_rows)}）"
                )
                continue
            for index, (live_row, dump_row) in enumerate(zip(live_rows, dump_rows, strict=True)):
                if live_row != dump_row:
                    problems.append(
                        f"{table}: 第 {index + 1} 行不一致（工作库 {live_row!r}，dump {dump_row!r}）"
                    )
                    break

        problems.extend(check_search_text(conn, prefix="工作库"))
        problems.extend(check_search_text(dump_conn, prefix="dump"))
    finally:
        dump_conn.close()
    return problems


def check_search_text(conn: sqlite3.Connection, *, prefix: str) -> list[str]:
    """search_text 必须等于名称表 + description 的稳定拼接。"""
    problems: list[str] = []
    rows = conn.execute("SELECT id, search_text, description FROM annotation ORDER BY id")
    for row in rows:
        expected = search_text_for(names_for(conn, row["id"]), row["description"])
        if row["search_text"] != expected:
            problems.append(f"{prefix} {row['id']}: search_text 与名称表不一致")
    return problems


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")]


def _rows(conn: sqlite3.Connection, table: str, columns: list[str]) -> list[tuple[Any, ...]]:
    column_sql = ", ".join(columns)
    rows = conn.execute(f"SELECT {column_sql} FROM {table} ORDER BY {ORDER_BY[table]}")
    return [tuple(row[column] for column in columns) for row in rows]


def _literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, bytes):
        return "X'" + value.hex() + "'"
    return "'" + str(value).replace("'", "''") + "'"


__all__ = [
    "SCHEMA_SQL",
    "check_search_text",
    "dump_sql",
    "rebuild_indexes",
    "restore_sql",
    "verify_dump",
]
