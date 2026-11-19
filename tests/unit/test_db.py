"""数据库层：CRUD、搜索、软删除、dump/restore/verify（TASK-0004）。"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from mapcreator.cli import app
from mapcreator.db import repo
from mapcreator.models import Annotation, AnnotationName

runner = CliRunner()


@pytest.fixture()
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = repo.connect(tmp_path / "annotations.db")
    repo.init_schema(connection, world_id="aetheria", default_lang="zh")
    yield connection
    connection.close()


def make_annotation(
    annotation_id: str,
    *,
    zh: str,
    en: str | None = None,
    alias: str | None = None,
    kind: str = "city",
    rank: int = 2,
    description: str | None = None,
    lon: float = 12.0,
    lat: float = 8.5,
) -> Annotation:
    names = [AnnotationName(lang="zh", name=zh, is_primary=True)]
    if en is not None:
        names.append(AnnotationName(lang="en", name=en, role="alias"))
    if alias is not None:
        names.append(AnnotationName(lang="en", name=alias, role="alias"))
    return Annotation(
        id=annotation_id,
        kind=kind,
        lon=lon,
        lat=lat,
        rank=rank,
        description=description,
        names=names,
    )


def test_upsert_and_get_with_names_and_search_text(conn: sqlite3.Connection) -> None:
    stored = repo.upsert_annotation(
        conn,
        make_annotation("anno.city.silverrun", zh="银流城", en="Silverrun", description="河港"),
    )

    assert stored.revision == 1
    assert [name.name for name in stored.names] == ["银流城", "Silverrun"]
    row = conn.execute("SELECT search_text FROM annotation WHERE id = ?", (stored.id,)).fetchone()
    assert row["search_text"] == "Silverrun 银流城 河港"


def test_missing_primary_name_is_rejected(conn: sqlite3.Connection) -> None:
    with pytest.raises(ValidationError):
        Annotation(
            id="anno.city.nameless",
            kind="city",
            lon=12.0,
            lat=8.5,
            names=[AnnotationName(lang="zh", name="无名", is_primary=False)],
        )

    # 绕过模型校验直接构造（模拟服务端内部调用）时，repo 仍必须拒绝。
    sneaky = Annotation.model_construct(
        id="anno.city.nameless",
        kind="city",
        lon=12.0,
        lat=8.5,
        names=[AnnotationName(lang="zh", name="无名", is_primary=False)],
    )
    with pytest.raises(Exception) as excinfo:
        repo.upsert_annotation(conn, sneaky)
    assert getattr(excinfo.value, "code", None) == "PRIMARY_NAME_MISSING"


def test_primary_name_unique_index(conn: sqlite3.Connection) -> None:
    repo.upsert_annotation(conn, make_annotation("anno.city.silverrun", zh="银流城"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO annotation_name(annotation_id, lang, name, role, is_primary) "
            "VALUES('anno.city.silverrun', 'en', 'Duplicate', 'name', 1)"
        )


def test_revision_conflict(conn: sqlite3.Connection) -> None:
    first = repo.upsert_annotation(conn, make_annotation("anno.city.silverrun", zh="银流城"))
    second = repo.upsert_annotation(conn, first.model_copy(update={"rank": 3}))
    assert second.revision == 2

    stale = first.model_copy(update={"rank": 4})
    with pytest.raises(Exception) as excinfo:
        repo.upsert_annotation(conn, stale)
    assert getattr(excinfo.value, "code", None) == "REVISION_CONFLICT"


def test_search_short_query_uses_like(conn: sqlite3.Connection) -> None:
    repo.upsert_annotation(conn, make_annotation("anno.city.silverrun", zh="上海", en="Shanghai"))

    assert [hit["id"] for hit in repo.search(conn, "上海")] == ["anno.city.silverrun"]
    assert [hit["id"] for hit in repo.search(conn, "上")] == ["anno.city.silverrun"]
    assert [hit["id"] for hit in repo.search(conn, "银流")] == []


def test_search_long_query_uses_fts(conn: sqlite3.Connection) -> None:
    repo.upsert_annotation(
        conn,
        make_annotation("anno.city.silverrun", zh="银流城", en="Silverrun", alias="Silvertown"),
    )

    assert [hit["id"] for hit in repo.search(conn, "银流城")] == ["anno.city.silverrun"]
    assert [hit["id"] for hit in repo.search(conn, "Silverrun")] == ["anno.city.silverrun"]
    assert [hit["id"] for hit in repo.search(conn, "silvertown")] == ["anno.city.silverrun"]
    assert repo.search(conn, "silvertown", lang="ja") == []


def test_soft_delete_and_restore(conn: sqlite3.Connection) -> None:
    stored = repo.upsert_annotation(conn, make_annotation("anno.city.silverrun", zh="银流城"))

    repo.soft_delete(conn, stored.id, revision=stored.revision)
    assert repo.get_annotation(conn, stored.id) is None
    assert repo.all_annotations(conn) == []
    assert repo.search(conn, "银流城") == []

    repo.restore(conn, stored.id)
    restored = repo.get_annotation(conn, stored.id)
    assert restored is not None
    assert restored.revision == 3


def test_fts_and_rtree_triggers(conn: sqlite3.Connection) -> None:
    stored = repo.upsert_annotation(conn, make_annotation("anno.city.silverrun", zh="银流城"))

    assert conn.execute("SELECT count(*) FROM annotation_fts").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM annotation_rtree").fetchone()[0] == 1
    bbox = conn.execute(
        "SELECT min_lon, max_lon, min_lat, max_lat FROM annotation_rtree WHERE fid = ?",
        (conn.execute("SELECT fid FROM annotation WHERE id = ?", (stored.id,)).fetchone()[0],),
    ).fetchone()
    assert tuple(bbox) == (12.0, 12.0, 8.5, 8.5)


def test_dump_restore_roundtrip_is_byte_identical(conn: sqlite3.Connection, tmp_path: Path) -> None:
    repo.upsert_annotation(
        conn, make_annotation("anno.city.silverrun", zh="银流城", en="Silverrun")
    )
    repo.upsert_annotation(
        conn,
        make_annotation(
            "anno.hospital.lumen", zh="流明医院", kind="hospital", rank=4, lat=8.52, lon=12.05
        ),
    )
    first = tmp_path / "first.sql"
    repo.dump_sql(conn, first)

    rebuilt = repo.connect(tmp_path / "rebuilt.db")
    try:
        repo.init_schema(rebuilt, world_id="aetheria", default_lang="zh")
        repo.restore_sql(rebuilt, first)
        second = tmp_path / "second.sql"
        repo.dump_sql(rebuilt, second)
        assert second.read_bytes() == first.read_bytes()
        assert repo.verify_dump(rebuilt, first) == []
    finally:
        rebuilt.close()


def test_verify_dump_detects_search_text_drift(conn: sqlite3.Connection, tmp_path: Path) -> None:
    repo.upsert_annotation(conn, make_annotation("anno.city.silverrun", zh="银流城"))
    path = tmp_path / "annotations.sql"
    repo.dump_sql(conn, path)

    conn.execute("UPDATE annotation SET search_text = 'broken' WHERE id = 'anno.city.silverrun'")

    problems = repo.verify_dump(conn, path)
    assert any("search_text" in problem for problem in problems)


def test_cli_import_export_and_dump_roundtrip(tmp_path: Path) -> None:
    mini = Path(__file__).resolve().parents[1] / "fixtures" / "mini-world"
    db_path = tmp_path / "annotations.db"
    dump_path = tmp_path / "annotations.sql"
    export_path = tmp_path / "export.json"

    result = runner.invoke(
        app,
        [
            "annotations",
            "import",
            "--file",
            str(mini / "annotations.json"),
            "--db",
            str(db_path),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout)["count"] == 8

    result = runner.invoke(
        app, ["db", "dump", "--db", str(db_path), "--out", str(dump_path), "--json"]
    )
    assert result.exit_code == 0, result.stdout

    result = runner.invoke(
        app, ["db", "verify-dump", "--db", str(db_path), "--in", str(dump_path), "--json"]
    )
    assert result.exit_code == 0, result.stdout

    result = runner.invoke(
        app, ["annotations", "export", "--db", str(db_path), "--out", str(export_path), "--json"]
    )
    assert result.exit_code == 0, result.stdout
    exported = json.loads(export_path.read_text(encoding="utf-8"))
    assert len(exported["annotations"]) == 8
    assert [item["id"] for item in exported["annotations"]] == sorted(
        item["id"] for item in exported["annotations"]
    )
