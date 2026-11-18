"""CLI 入口（Typer）。

骨架阶段：所有子命令已注册，但行为统一为 `NotImplementedYet`，
退出码 4 + `code: NOT_IMPLEMENTED`，指向 TODO.md 中的具体任务。
这样 `mapcreator --help` 与命令清单从第一天起就是稳定契约。

统一 JSON 输出（AGENTS.md §3）：
    ok / command / duration_ms / errors[] / warnings[] / artifacts[]
退出码：0 成功、1 数据失败、2 用法/配置错误、3 环境缺失、4 内部错误/未实现。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import typer

from . import __version__
from . import doctor as doctor_mod
from .errors import ConfigurationError, DataValidationError, EnvironmentError_, MapCreatorError

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="MapCreator：本地优先、Python 主导、可缩放分级标注的架空世界地图工具。",
)
db_app = typer.Typer(
    no_args_is_help=True, help="数据库维护：dump / restore / verify-dump / migrate。"
)
annotations_app = typer.Typer(no_args_is_help=True, help="标注导入导出。")
geometry_app = typer.Typer(no_args_is_help=True, help="几何导入导出。")
app.add_typer(db_app, name="db")
app.add_typer(annotations_app, name="annotations")
app.add_typer(geometry_app, name="geometry")

EXIT_OK = 0
EXIT_DATA = 1
EXIT_USAGE = 2
EXIT_ENV = 3
EXIT_INTERNAL = 4


def _exit_code_for(exc: MapCreatorError) -> int:
    if isinstance(exc, ConfigurationError):
        return EXIT_USAGE
    if isinstance(exc, DataValidationError):
        return EXIT_DATA
    if isinstance(exc, EnvironmentError_):
        return EXIT_ENV
    return EXIT_INTERNAL


def _finish(
    command: str,
    *,
    as_json: bool,
    started: float,
    errors: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    artifacts: list[str] | None = None,
    extra: dict[str, Any] | None = None,
    exit_code: int = EXIT_OK,
) -> None:
    payload: dict[str, Any] = {
        "ok": exit_code == EXIT_OK,
        "command": command,
        "version": __version__,
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "errors": errors or [],
        "warnings": warnings or [],
        "artifacts": artifacts or [],
    }
    if extra:
        payload.update(extra)
    if as_json:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    elif payload["ok"]:
        typer.echo(f"✓ {command} 完成（{payload['duration_ms']} ms）")
    else:
        for err in payload["errors"]:
            typer.secho(f"✗ {err.get('code')}: {err.get('message')}", fg="red", err=True)
            if err.get("remediation"):
                typer.echo(f"  修复建议：{err['remediation']}", err=True)
    raise typer.Exit(code=exit_code)


def _todo(command: str, feature: str, task: str, as_json: bool) -> None:
    """骨架阶段占位：统一产出可解析的 JSON，而不是 traceback。"""
    started = time.perf_counter()
    err = MapCreatorError(
        code="NOT_IMPLEMENTED",
        message=f"{feature} 尚未实现（{command}）",
        remediation=f"见 TODO.md 的 {task}",
        details={"task": task},
    ).to_dict()
    _finish(command, as_json=as_json, started=started, errors=[err], exit_code=EXIT_INTERNAL)


@app.callback()
def main_callback(
    version: bool = typer.Option(False, "--version", help="打印版本并退出。"),
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit(code=EXIT_OK)


@app.command()
def doctor(json_output: bool = typer.Option(False, "--json", help="结构化 JSON 输出。")) -> None:
    """环境自检：Python / uv / Node / SQLite FTS5+RTree+trigram / Playwright / 可选工具。"""
    started = time.perf_counter()
    checks = doctor_mod.collect_checks()
    failures = [check for check in checks if check.required and check.status != "ok"]
    errors = [
        {
            "code": "ENV_MISSING",
            "message": f"{check.name} 不满足要求：{check.value}",
            "path": None,
            "feature_id": None,
            "details": {"check": check.name},
            "remediation": check.remediation,
        }
        for check in failures
    ]
    warnings = [
        f"{check.name}: {check.value}"
        for check in checks
        if not check.required and check.status != "ok"
    ]
    if not json_output:
        for line in doctor_mod.render_lines(checks):
            typer.echo(line)
    _finish(
        "doctor",
        as_json=json_output,
        started=started,
        errors=errors,
        warnings=warnings,
        extra={"checks": [check.to_dict() for check in checks]},
        exit_code=EXIT_ENV if failures else EXIT_OK,
    )


@app.command()
def describe(json_output: bool = typer.Option(False, "--json")) -> None:
    """世界概览：bounds、kind 清单、要素/标注计数。"""
    _todo("describe", "世界概览", "TASK-0003", json_output)


@app.command()
def validate(
    fix: bool = typer.Option(False, "--fix", help="允许 shapely.make_valid 修复并记录警告。"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """只校验真源，不写任何产物。"""
    _todo("validate", f"数据校验（fix={fix}）", "TASK-0005", json_output)


@app.command()
def build(
    clean: bool = typer.Option(False, "--clean"),
    watch: bool = typer.Option(False, "--watch"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """构建 build/（原子发布）。"""
    _todo("build", f"构建（clean={clean}, watch={watch}）", "TASK-0005", json_output)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="默认仅本机。"),
    port: int = typer.Option(8765, "--port"),
    dev: bool = typer.Option(False, "--dev"),
    enable_edit: bool = typer.Option(False, "--enable-edit"),
    enable_sql: bool = typer.Option(False, "--enable-sql"),
) -> None:
    """启动本地应用（默认 http://127.0.0.1:8765）。"""
    _todo(
        "serve",
        f"本地服务（host={host}, port={port}, dev={dev}, edit={enable_edit}, sql={enable_sql}）",
        "TASK-0006",
        True,
    )


@app.command()
def check(
    full: bool = typer.Option(False, "--full", help="格式/类型/单测/校验/构建/E2E 全跑。"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """质量门禁。"""
    _todo("check", f"质量检查（full={full}）", "TASK-0011", json_output)


@app.command()
def screenshot(
    url: str = typer.Option(..., "--url"),
    out: Path = typer.Option(Path("artifacts/shot.png"), "--out"),
) -> None:
    """用 Playwright 截图（证据留存）。"""
    _todo("screenshot", f"截图（{url} → {out}）", "TASK-0011", True)


@app.command()
def query(
    sql: str = typer.Option(..., "--sql"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """只读 SQL 查询（仅 SELECT/WITH）。"""
    _todo("query", "只读 SQL", "TASK-0008", json_output)


@app.command()
def setup(json_output: bool = typer.Option(False, "--json")) -> None:
    """幂等地准备前端构建产物与本地数据目录。"""
    _todo("setup", "初始化", "TASK-0002", json_output)


@app.command(name="format")
def format_all(json_output: bool = typer.Option(False, "--json")) -> None:
    """归一化 GeoJSON 文本（稳定排序、6 位小数）。"""
    _todo("format", "格式化", "TASK-0005", json_output)


@app.command()
def export(
    static: bool = typer.Option(False, "--static"),
    qgis: bool = typer.Option(False, "--qgis"),
    out: Path = typer.Option(Path("dist"), "--out"),
) -> None:
    """导出（静态站点推迟到 M5 之后；QGIS 见 TASK-0010）。"""
    _todo("export", f"导出（static={static}, qgis={qgis}, out={out}）", "TASK-0010", True)


@app.command()
def openapi(out: Path = typer.Option(Path("docs/openapi.json"), "--out")) -> None:
    """导出 OpenAPI 契约到文件。"""
    _todo("openapi", f"导出 OpenAPI（{out}）", "TASK-0006", True)


@app.command()
def backup(out: Path = typer.Option(Path("backups"), "--out")) -> None:
    """备份：源码 + annotations.sql 打包。"""
    _todo("backup", f"备份到 {out}", "TASK-0004", True)


@db_app.command("dump")
def db_dump(out: Path = typer.Option(Path("world/annotations.sql"), "--out")) -> None:
    """把工作库导出为可提交的 SQL dump（只导逻辑表）。"""
    _todo("db dump", f"导出 dump（{out}）", "TASK-0004", True)


@db_app.command("restore")
def db_restore(infile: Path = typer.Option(Path("world/annotations.sql"), "--in")) -> None:
    """从 dump 恢复工作库并重建 FTS/RTree。"""
    _todo("db restore", f"恢复（{infile}）", "TASK-0004", True)


@db_app.command("verify-dump")
def db_verify(infile: Path = typer.Option(Path("world/annotations.sql"), "--in")) -> None:
    """校验 dump 与工作库一致（含 search_text 一致性）。"""
    _todo("db verify-dump", f"校验 dump（{infile}）", "TASK-0004", True)


@db_app.command("migrate")
def db_migrate() -> None:
    """执行待应用的迁移。"""
    _todo("db migrate", "迁移", "TASK-0004", True)


@annotations_app.command("export")
def ann_export(
    json_output: bool = typer.Option(False, "--json"),
    out: Path = typer.Option(Path("build/annotations.export.json"), "--out"),
) -> None:
    """导出标注 JSON 快照（只读）。"""
    _todo("annotations export", f"导出标注（{out}）", "TASK-0004", json_output)


@annotations_app.command("import")
def ann_import(
    path: Path = typer.Option(..., "--json-file", "--file", help="标注 JSON 文件。"),
) -> None:
    """从 JSON 批量导入标注。"""
    _todo("annotations import", f"导入标注（{path}）", "TASK-0004", True)


@annotations_app.command("import-geojson")
def ann_import_geojson(path: Path = typer.Option(..., "--geojson")) -> None:
    """从 QGIS 导出的 GeoJSON 导入标注。"""
    _todo("annotations import --geojson", f"导入 GeoJSON 标注（{path}）", "TASK-0010", True)


@geometry_app.command("import")
def geo_import(directory: Path = typer.Option(..., "--dir")) -> None:
    """导入 QGIS 编辑后的几何目录。"""
    _todo("geometry import", f"导入几何（{directory}）", "TASK-0010", True)


def run() -> None:
    """控制台入口；把领域异常映射为稳定退出码。"""
    try:
        app()
    except MapCreatorError as exc:
        typer.secho(json.dumps(exc.to_dict(), ensure_ascii=False), fg="red", err=True)
        sys.exit(_exit_code_for(exc))


if __name__ == "__main__":  # pragma: no cover
    run()
