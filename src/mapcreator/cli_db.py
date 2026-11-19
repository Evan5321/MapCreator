"""`db` 与 `annotations` 子命令（从 cli.py 拆出以保持单文件规模）。"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from .cli_support import EXIT_INTERNAL, exit_code_for, finish, todo
from .config import AppConfig, load_config
from .data.annotations import load_export
from .db import repo
from .errors import DataValidationError, MapCreatorError

db_app = typer.Typer(
    no_args_is_help=True, help="数据库维护：init / dump / restore / verify-dump / migrate。"
)
annotations_app = typer.Typer(no_args_is_help=True, help="标注导入导出。")


def _db_path(config: AppConfig, path: Path | None) -> Path:
    return path if path is not None else config.root / "world" / "annotations.db"


def _dump_path(config: AppConfig, path: Path | None) -> Path:
    return path if path is not None else config.root / "world" / "annotations.sql"


def _require_file(path: Path, *, code: str, label: str) -> None:
    if not path.is_file():
        raise DataValidationError(
            code=code,
            message=f"{label}不存在：{path}",
            path=path,
            remediation="先运行 `mapcreator db init` / `db dump`，或用 --db/--in 指定路径",
        )


def _db_error(exc: sqlite3.Error) -> dict[str, Any]:
    return {
        "code": "DB_ERROR",
        "message": f"SQLite 操作失败：{exc}",
        "path": None,
        "feature_id": None,
        "details": {},
        "remediation": "检查数据库文件、磁盘空间与安全软件是否拦截写入",
    }


def _run(command: str, as_json: bool, body: Callable[[], dict[str, Any] | None]) -> None:
    started = time.perf_counter()
    try:
        extra = body()
    except MapCreatorError as exc:
        finish(
            command,
            as_json=as_json,
            started=started,
            errors=[exc.to_dict()],
            exit_code=exit_code_for(exc),
        )
    except sqlite3.Error as exc:
        finish(
            command,
            as_json=as_json,
            started=started,
            errors=[_db_error(exc)],
            exit_code=EXIT_INTERNAL,
        )
    finish(command, as_json=as_json, started=started, extra=extra)


@db_app.command("init")
def db_init(
    db: Path | None = typer.Option(None, "--db"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """创建（或补齐）工作库 schema，幂等。"""

    def body() -> dict[str, Any]:
        config = load_config()
        path = _db_path(config, db)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = repo.connect(path)
        try:
            repo.init_schema(conn, world_id=config.world.id, default_lang=config.world.default_lang)
        finally:
            conn.close()
        return {"db": path.as_posix(), "schema_version": repo.SCHEMA_VERSION}

    _run("db init", json_output, body)


@db_app.command("dump")
def db_dump(
    out: Path | None = typer.Option(None, "--out"),
    db: Path | None = typer.Option(None, "--db"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """把工作库导出为可提交的 SQL dump（只导逻辑表）。"""

    def body() -> dict[str, Any]:
        config = load_config()
        path = _db_path(config, db)
        target = _dump_path(config, out)
        _require_file(path, code="DB_MISSING", label="工作库")
        conn = repo.connect(path)
        try:
            repo.dump_sql(conn, target)
        finally:
            conn.close()
        return {"db": path.as_posix(), "artifacts": [target.as_posix()]}

    _run("db dump", json_output, body)


@db_app.command("restore")
def db_restore(
    infile: Path | None = typer.Option(None, "--in"),
    db: Path | None = typer.Option(None, "--db"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """从 dump 恢复工作库并重建 FTS/RTree。"""

    def body() -> dict[str, Any]:
        config = load_config()
        path = _db_path(config, db)
        source = _dump_path(config, infile)
        _require_file(source, code="DUMP_MISSING", label="dump 文件")
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = repo.connect(path)
        try:
            repo.init_schema(conn, world_id=config.world.id, default_lang=config.world.default_lang)
            repo.restore_sql(conn, source)
            problems = repo.verify_dump(conn, source)
        finally:
            conn.close()
        if problems:
            raise DataValidationError(
                code="DUMP_MISMATCH",
                message=f"恢复后与 dump 不一致（{len(problems)} 项）",
                path=source,
                remediation="检查备份文件是否被手工修改；必要时重新 db dump",
                details={"problems": problems},
            )
        return {"db": path.as_posix(), "source": source.as_posix()}

    _run("db restore", json_output, body)


@db_app.command("verify-dump")
def db_verify(
    infile: Path | None = typer.Option(None, "--in"),
    db: Path | None = typer.Option(None, "--db"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """校验 dump 与工作库一致（行数、主键、search_text）。"""

    def body() -> dict[str, Any]:
        config = load_config()
        path = _db_path(config, db)
        source = _dump_path(config, infile)
        _require_file(path, code="DB_MISSING", label="工作库")
        _require_file(source, code="DUMP_MISSING", label="dump 文件")
        conn = repo.connect(path)
        try:
            problems = repo.verify_dump(conn, source)
        finally:
            conn.close()
        if problems:
            raise DataValidationError(
                code="DUMP_MISMATCH",
                message=f"dump 与工作库不一致（{len(problems)} 项）",
                path=source,
                remediation="先 `db dump` 覆盖过期 dump，或修复工作库后重试",
                details={"problems": problems},
            )
        return {"db": path.as_posix(), "source": source.as_posix(), "checked": "logical-tables"}

    _run("db verify-dump", json_output, body)


@db_app.command("migrate")
def db_migrate(
    db: Path | None = typer.Option(None, "--db"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """执行待应用的迁移（当前只有 baseline schema，幂等）。"""

    def body() -> dict[str, Any]:
        config = load_config()
        path = _db_path(config, db)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = repo.connect(path)
        try:
            repo.init_schema(conn, world_id=config.world.id, default_lang=config.world.default_lang)
            version = repo.schema_version(conn)
        finally:
            conn.close()
        return {"db": path.as_posix(), "schema_version": version}

    _run("db migrate", json_output, body)


@annotations_app.command("export")
def ann_export(
    db: Path | None = typer.Option(None, "--db"),
    out: Path | None = typer.Option(None, "--out"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """导出标注 JSON 快照（只读、稳定排序）。"""

    def body() -> dict[str, Any]:
        config = load_config()
        path = _db_path(config, db)
        target = out if out is not None else config.root / "build" / "annotations.export.json"
        _require_file(path, code="DB_MISSING", label="工作库")
        conn = repo.connect(path)
        try:
            annotations = repo.export_annotations(conn)
        finally:
            conn.close()
        target.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(
            {"annotations": annotations}, ensure_ascii=False, indent=2, sort_keys=True
        )
        target.write_text(text + "\n", encoding="utf-8", newline="\n")
        return {"artifacts": [target.as_posix()], "count": len(annotations)}

    _run("annotations export", json_output, body)


@annotations_app.command("import")
def ann_import(
    path: Path = typer.Option(..., "--json-file", "--file", help="标注 JSON 文件。"),
    db: Path | None = typer.Option(None, "--db"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """从 JSON 批量导入标注（逐条校验，单事务）。"""

    def body() -> dict[str, Any]:
        config = load_config()
        annotations = load_export(path)
        target = _db_path(config, db)
        target.parent.mkdir(parents=True, exist_ok=True)
        conn = repo.connect(target)
        try:
            repo.init_schema(conn, world_id=config.world.id, default_lang=config.world.default_lang)
            for annotation in annotations:
                repo.upsert_annotation(conn, annotation)
        finally:
            conn.close()
        return {"db": target.as_posix(), "count": len(annotations)}

    _run("annotations import", json_output, body)


@annotations_app.command("import-geojson")
def ann_import_geojson(path: Path = typer.Option(..., "--geojson")) -> None:
    """从 QGIS 导出的 GeoJSON 导入标注。"""
    todo("annotations import --geojson", f"导入 GeoJSON 标注（{path}）", "TASK-0010", True)
