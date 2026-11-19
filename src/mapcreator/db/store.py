"""标注 / 名称的 CRUD、搜索与软删除（repo 的实现拆分）。

规则：写入必须参数化 + 单事务；`search_text` 同事务重算；`revision` 每次 +1。
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from ..errors import DataValidationError
from ..models import Annotation, AnnotationName


def names_for(conn: sqlite3.Connection, annotation_id: str) -> list[AnnotationName]:
    rows = conn.execute(
        """SELECT lang, name, role, is_primary FROM annotation_name
           WHERE annotation_id = ?
           ORDER BY is_primary DESC, lang ASC, role ASC, name ASC""",
        (annotation_id,),
    ).fetchall()
    return [
        AnnotationName(
            lang=row["lang"],
            name=row["name"],
            role=row["role"],
            is_primary=bool(row["is_primary"]),
        )
        for row in rows
    ]


def search_text_for(names: list[AnnotationName], description: str | None) -> str:
    """名称（全语种 + 别名）+ description，按稳定顺序空格连接。"""
    ordered = sorted(names, key=lambda item: (item.lang, item.role, item.name))
    parts = [name.name for name in ordered]
    if description:
        parts.append(description)
    return " ".join(parts)


def get_annotation(
    conn: sqlite3.Connection, annotation_id: str, *, include_deleted: bool = False
) -> Annotation | None:
    """按 ID 取详情（含全部名称）；默认把软删除视为不存在。"""
    sql = "SELECT * FROM annotation WHERE id = ?"
    if not include_deleted:
        sql += " AND deleted_at IS NULL"
    row = conn.execute(sql, (annotation_id,)).fetchone()
    return None if row is None else _row_to_annotation(conn, row)


def all_annotations(conn: sqlite3.Connection, *, include_deleted: bool = False) -> list[Annotation]:
    """按 ID 稳定排序返回全部标注（dump / 导出 / 构建复用）。"""
    sql = "SELECT * FROM annotation"
    if not include_deleted:
        sql += " WHERE deleted_at IS NULL"
    sql += " ORDER BY id ASC"
    return [_row_to_annotation(conn, row) for row in conn.execute(sql)]


def search(
    conn: sqlite3.Connection,
    query: str,
    *,
    lang: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """>=3 字符走 FTS5 trigram，1-2 字符回退 LIKE（D-017）。"""
    text = query.strip()
    if not text:
        return []
    if not 1 <= limit <= 100:
        raise DataValidationError(
            code="LIMIT_INVALID", message=f"limit 必须在 1..100：{limit}", remediation="调整 limit"
        )
    try:
        if len(text) >= 3:
            rows = _search_fts(conn, text, lang=lang, limit=limit)
        else:
            rows = _search_like(conn, text, lang=lang, limit=limit)
    except sqlite3.OperationalError:
        # FTS 查询语法异常时退化为 LIKE（短词/特殊字符/索引未建）
        rows = _search_like(conn, text, lang=lang, limit=limit)
    return [
        {
            "id": row["id"],
            "kind": row["kind"],
            "rank": row["rank"],
            "lon": row["lon"],
            "lat": row["lat"],
            "name": row["name"],
            "lang": row["name_lang"],
        }
        for row in rows
    ]


def _search_fts(
    conn: sqlite3.Connection, text: str, *, lang: str | None, limit: int
) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT v.id, v.kind, v.rank, v.lon, v.lat, v.name, v.name_lang
           FROM annotation_fts
           JOIN annotation_v v ON v.fid = annotation_fts.rowid
           WHERE annotation_fts MATCH ?
             AND v.deleted_at IS NULL
             AND (? IS NULL OR v.id IN (SELECT annotation_id FROM annotation_name WHERE lang = ?))
           ORDER BY v.rank ASC, COALESCE(v.name, '') ASC, v.id ASC
           LIMIT ?""",
        (_fts_query(text), lang, lang, limit),
    ).fetchall()


def _search_like(
    conn: sqlite3.Connection, text: str, *, lang: str | None, limit: int
) -> list[sqlite3.Row]:
    pattern = f"%{_like_escape(text)}%"
    return conn.execute(
        """SELECT v.id, v.kind, v.rank, v.lon, v.lat, v.name, v.name_lang
           FROM annotation_v v
           WHERE v.deleted_at IS NULL
             AND (v.name LIKE ? ESCAPE '\\' OR v.search_text LIKE ? ESCAPE '\\')
             AND (? IS NULL OR v.id IN (SELECT annotation_id FROM annotation_name WHERE lang = ?))
           ORDER BY v.rank ASC, COALESCE(v.name, '') ASC, v.id ASC
           LIMIT ?""",
        (pattern, pattern, lang, lang, limit),
    ).fetchall()


def _fts_query(text: str) -> str:
    """按短语查询，避免用户输入被解释成 FTS 运算符。"""
    return '"' + text.replace('"', '""') + '"'


def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def upsert_annotation(
    conn: sqlite3.Connection,
    annotation: Annotation,
    *,
    now: datetime | None = None,
) -> Annotation:
    """插入或更新；旧 revision 冲突时抛 DataValidationError(REVISION_CONFLICT)。"""
    primaries = [name for name in annotation.names if name.is_primary]
    if len(primaries) != 1:
        raise DataValidationError(
            code="PRIMARY_NAME_MISSING",
            message=f"标注 {annotation.id} 必须恰好有一个 is_primary=1 的名称",
            feature_id=annotation.id,
            remediation="补上主名，并把其余名称标记为 role=alias",
        )
    timestamp = (now or datetime.now(UTC)).isoformat(timespec="seconds")
    updated_at = _iso(annotation.updated_at) or timestamp
    deleted_at = _iso(annotation.deleted_at)
    search_text = search_text_for(annotation.names, annotation.description)
    attrs = json.dumps(annotation.attrs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    existing = conn.execute(
        "SELECT revision FROM annotation WHERE id = ?", (annotation.id,)
    ).fetchone()
    try:
        conn.execute("BEGIN")
        if existing is None:
            revision = annotation.revision
            conn.execute(
                """INSERT INTO annotation(id, kind, search_text, parent_id, geometry_id, lon, lat,
                       label_mode, rank, min_zoom, max_zoom, icon, description, attrs, revision,
                       updated_at, deleted_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    annotation.id,
                    annotation.kind,
                    search_text,
                    annotation.parent_id,
                    annotation.geometry_id,
                    annotation.lon,
                    annotation.lat,
                    annotation.label_mode,
                    annotation.rank,
                    annotation.min_zoom,
                    annotation.max_zoom,
                    annotation.icon,
                    annotation.description,
                    attrs,
                    revision,
                    updated_at,
                    deleted_at,
                ),
            )
        else:
            current = int(existing["revision"])
            if annotation.revision != current:
                raise DataValidationError(
                    code="REVISION_CONFLICT",
                    message=(
                        f"标注 {annotation.id} 的 revision 已过期："
                        f"提交 {annotation.revision}，库中 {current}"
                    ),
                    feature_id=annotation.id,
                    remediation="重新读取最新 revision 后再提交",
                )
            revision = current + 1
            conn.execute(
                """UPDATE annotation SET kind = ?, search_text = ?, parent_id = ?, geometry_id = ?,
                       lon = ?, lat = ?, label_mode = ?, rank = ?, min_zoom = ?, max_zoom = ?,
                       icon = ?, description = ?, attrs = ?, revision = ?, updated_at = ?,
                       deleted_at = ?
                   WHERE id = ?""",
                (
                    annotation.kind,
                    search_text,
                    annotation.parent_id,
                    annotation.geometry_id,
                    annotation.lon,
                    annotation.lat,
                    annotation.label_mode,
                    annotation.rank,
                    annotation.min_zoom,
                    annotation.max_zoom,
                    annotation.icon,
                    annotation.description,
                    attrs,
                    revision,
                    updated_at,
                    deleted_at,
                    annotation.id,
                ),
            )
            conn.execute("DELETE FROM annotation_name WHERE annotation_id = ?", (annotation.id,))
        conn.executemany(
            """INSERT INTO annotation_name(annotation_id, lang, name, role, is_primary)
               VALUES(?, ?, ?, ?, ?)""",
            [
                (annotation.id, name.lang, name.name, name.role, int(name.is_primary))
                for name in annotation.names
            ],
        )
        conn.execute("COMMIT")
    except BaseException:
        _rollback(conn)
        raise

    result = get_annotation(conn, annotation.id, include_deleted=True)
    assert result is not None
    return result


def soft_delete(
    conn: sqlite3.Connection,
    annotation_id: str,
    *,
    revision: int,
    now: datetime | None = None,
) -> None:
    """软删除（deleted_at 置值），不物理删除。"""
    timestamp = (now or datetime.now(UTC)).isoformat(timespec="seconds")
    _mutate_live(conn, annotation_id, revision, timestamp, "deleted_at = ?", timestamp)


def restore(conn: sqlite3.Connection, annotation_id: str) -> None:
    """恢复软删除的标注。"""
    row = conn.execute(
        "SELECT revision FROM annotation WHERE id = ? AND deleted_at IS NOT NULL",
        (annotation_id,),
    ).fetchone()
    if row is None:
        raise _not_found(annotation_id)
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    try:
        conn.execute("BEGIN")
        conn.execute(
            """UPDATE annotation SET deleted_at = NULL, revision = revision + 1, updated_at = ?
               WHERE id = ? AND revision = ?""",
            (timestamp, annotation_id, int(row["revision"])),
        )
        conn.execute("COMMIT")
    except BaseException:
        _rollback(conn)
        raise


def _mutate_live(
    conn: sqlite3.Connection,
    annotation_id: str,
    revision: int,
    timestamp: str,
    assignment: str,
    *params: Any,
) -> None:
    row = conn.execute(
        "SELECT revision FROM annotation WHERE id = ? AND deleted_at IS NULL", (annotation_id,)
    ).fetchone()
    if row is None:
        raise _not_found(annotation_id)
    if int(row["revision"]) != revision:
        raise DataValidationError(
            code="REVISION_CONFLICT",
            message=(
                f"标注 {annotation_id} 的 revision 已过期：提交 {revision}，库中 {row['revision']}"
            ),
            feature_id=annotation_id,
            remediation="重新读取最新 revision 后再提交",
        )
    try:
        conn.execute("BEGIN")
        conn.execute(
            f"UPDATE annotation SET {assignment}, revision = revision + 1, updated_at = ? "
            "WHERE id = ?",
            (*params, timestamp, annotation_id),
        )
        conn.execute("COMMIT")
    except BaseException:
        _rollback(conn)
        raise


def _not_found(annotation_id: str) -> DataValidationError:
    return DataValidationError(
        code="ANNOTATION_NOT_FOUND",
        message=f"标注不存在或已删除：{annotation_id}",
        feature_id=annotation_id,
        remediation="检查 ID，或先恢复该标注",
    )


def recompute_search_text(conn: sqlite3.Connection, annotation_id: str) -> str:
    """名称（全语种 + 别名）+ description，空格连接。"""
    row = conn.execute(
        "SELECT description FROM annotation WHERE id = ?", (annotation_id,)
    ).fetchone()
    if row is None:
        raise _not_found(annotation_id)
    text = search_text_for(names_for(conn, annotation_id), row["description"])
    try:
        conn.execute("BEGIN")
        conn.execute("UPDATE annotation SET search_text = ? WHERE id = ?", (text, annotation_id))
        conn.execute("COMMIT")
    except BaseException:
        _rollback(conn)
        raise
    return text


def export_annotations(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """导出可读 JSON（按 ID 稳定排序；不含软删除）。"""
    return [
        annotation.model_dump(mode="json")
        for annotation in all_annotations(conn, include_deleted=False)
    ]


def _row_to_annotation(conn: sqlite3.Connection, row: sqlite3.Row) -> Annotation:
    return Annotation(
        id=row["id"],
        kind=row["kind"],
        parent_id=row["parent_id"],
        geometry_id=row["geometry_id"],
        lon=row["lon"],
        lat=row["lat"],
        label_mode=row["label_mode"],
        rank=row["rank"],
        min_zoom=row["min_zoom"],
        max_zoom=row["max_zoom"],
        icon=row["icon"],
        description=row["description"],
        attrs=json.loads(row["attrs"]),
        revision=row["revision"],
        updated_at=_parse_dt(row["updated_at"]),
        deleted_at=_parse_dt(row["deleted_at"]),
        names=names_for(conn, row["id"]),
    )


def _parse_dt(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="seconds")


def _rollback(conn: sqlite3.Connection) -> None:
    with contextlib.suppress(sqlite3.Error):
        conn.execute("ROLLBACK")
