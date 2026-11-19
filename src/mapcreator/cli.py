"""CLI 入口（Typer）。

所有子命令共用 `cli_support` 的统一 JSON 输出与退出码；
未实现的子命令返回 `code: NOT_IMPLEMENTED`（退出码 4）并指向 TODO.md。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import typer

from . import __version__
from . import doctor as doctor_mod
from .build import pipeline as build_pipeline
from .cli_db import annotations_app, db_app
from .cli_support import (
    EXIT_ENV,
    EXIT_INTERNAL,
    EXIT_OK,
    exit_code_for,
    finish,
    todo,
)
from .config import load_config
from .data.world import describe_world
from .errors import MapCreatorError
from .schema_export import export_schemas

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="MapCreator：本地优先、Python 主导、可缩放分级标注的架空世界地图工具。",
)
geometry_app = typer.Typer(no_args_is_help=True, help="几何导入导出。")
app.add_typer(db_app, name="db")
app.add_typer(annotations_app, name="annotations")
app.add_typer(geometry_app, name="geometry")


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
    finish(
        "doctor",
        as_json=json_output,
        started=started,
        errors=errors,
        warnings=warnings,
        extra={"checks": [check.to_dict() for check in checks]},
        exit_code=EXIT_ENV if failures else EXIT_OK,
    )


@app.command()
def describe(
    root: Path | None = typer.Option(None, "--root", help="世界数据目录（默认 <仓库根>/world）。"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """世界概览：bounds、kind 清单、要素/标注计数。只读，不写任何产物。"""
    started = time.perf_counter()
    try:
        config = load_config()
        data_root = root if root is not None else config.root / "world"
        payload = describe_world(config, data_root)
    except MapCreatorError as exc:
        finish(
            "describe",
            as_json=json_output,
            started=started,
            errors=[exc.to_dict()],
            exit_code=exit_code_for(exc),
        )

    warnings: list[str] = []
    if payload["bounds"] is None:
        warnings.append("没有几何或标注，无法推导 bounds（可在 config/world.toml 显式指定）")
    if not json_output:
        bounds = payload["bounds"]
        typer.echo(f"世界：{payload['world']['name']}（{payload['world']['id']}）")
        typer.echo(
            "bounds：" + ("未定义" if bounds is None else ", ".join(f"{v:.6f}" for v in bounds))
        )
        counts = payload["counts"]
        typer.echo(f"几何：{counts['geometry_total']} 条；标注：{counts['annotation_total']} 个")
    finish(
        "describe",
        as_json=json_output,
        started=started,
        warnings=warnings,
        extra=payload,
    )


@app.command(name="schema")
def schema_command(
    out: Path = typer.Option(Path("schemas"), "--out", help="输出目录。"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """从 Pydantic 模型导出 JSON Schema（生成物，禁止手改）。"""
    started = time.perf_counter()
    try:
        written = export_schemas(out)
    except OSError as exc:
        finish(
            "schema",
            as_json=json_output,
            started=started,
            errors=[
                {
                    "code": "SCHEMA_WRITE_FAILED",
                    "message": f"写入 schema 失败：{exc}",
                    "path": str(out),
                    "feature_id": None,
                    "details": {},
                    "remediation": "确认输出目录可写",
                }
            ],
            exit_code=4,
        )
    finish(
        "schema",
        as_json=json_output,
        started=started,
        artifacts=[path.as_posix() for path in written],
    )


@app.command()
def validate(
    fix: bool = typer.Option(False, "--fix", help="允许 shapely.make_valid 修复并记录警告。"),
    root: Path | None = typer.Option(None, "--root", help="世界数据目录（默认 <仓库根>/world）。"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """只校验真源，不写任何产物。"""
    started = time.perf_counter()
    try:
        config = load_config()
        payload = build_pipeline.validate(config, data_root=root)
    except MapCreatorError as exc:
        finish(
            "validate",
            as_json=json_output,
            started=started,
            errors=[exc.to_dict()],
            exit_code=exit_code_for(exc),
        )

    warnings = list(payload["warnings"])
    if fix:
        warnings.append("--fix 尚未接入自动修复；本次只做只读校验")
    if not json_output:
        counts = payload["counts"]
        typer.echo(
            f"{payload['world']['name']}：几何 {counts['geometry_total']} 条，"
            f"标注 {counts['annotation_total']} 个"
        )
    finish(
        "validate",
        as_json=json_output,
        started=started,
        warnings=warnings,
        extra=payload,
    )


@app.command()
def build(
    clean: bool = typer.Option(False, "--clean"),
    watch: bool = typer.Option(False, "--watch"),
    root: Path | None = typer.Option(None, "--root", help="世界数据目录（默认 <仓库根>/world）。"),
    out: Path | None = typer.Option(None, "--out", help="构建输出目录（默认 <仓库根>/build）。"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """构建 build/（原子发布）。"""
    started = time.perf_counter()
    if watch:
        todo("build --watch", "监听并增量构建", "TASK-0012", json_output)

    try:
        config = load_config()
        payload = build_pipeline.run(config, data_root=root, out_dir=out, clean=clean)
    except MapCreatorError as exc:
        finish(
            "build",
            as_json=json_output,
            started=started,
            errors=[exc.to_dict()],
            exit_code=exit_code_for(exc),
        )

    manifest = payload["manifest"]
    artifacts = [f"{payload['build_dir']}/{item['path']}" for item in manifest["files"]]
    artifacts.append(f"{payload['build_dir']}/manifest.json")
    if not json_output:
        counts = manifest["counts"]
        typer.echo(
            f"构建完成：{payload['build_dir']}（几何 {counts['geometry_total']}，"
            f"标注 {counts['annotation_total']}，build_version={manifest['build_version']}）"
        )
    finish(
        "build",
        as_json=json_output,
        started=started,
        warnings=payload["warnings"],
        extra={"build_dir": payload["build_dir"], "manifest": manifest},
        artifacts=artifacts,
    )


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="默认仅本机。"),
    port: int = typer.Option(8765, "--port"),
    dev: bool = typer.Option(False, "--dev"),
    enable_edit: bool = typer.Option(False, "--enable-edit"),
    enable_sql: bool = typer.Option(False, "--enable-sql"),
) -> None:
    """启动本地应用（默认 http://127.0.0.1:8765）。"""
    from .server import app as server_app

    typer.echo(f"MapCreator → http://{host}:{port}")
    try:
        server_app.run(host, port, dev=dev, enable_edit=enable_edit, enable_sql=enable_sql)
    except MapCreatorError as exc:
        typer.secho(json.dumps(exc.to_dict(), ensure_ascii=False), fg="red", err=True)
        raise typer.Exit(code=exit_code_for(exc)) from exc
    except OSError as exc:
        typer.secho(f"启动失败：{exc}", fg="red", err=True)
        raise typer.Exit(code=EXIT_INTERNAL) from exc


@app.command()
def check(
    full: bool = typer.Option(False, "--full", help="格式/类型/单测/校验/构建/E2E 全跑。"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """质量门禁。"""
    todo("check", f"质量检查（full={full}）", "TASK-0011", json_output)


@app.command()
def screenshot(
    url: str = typer.Option(..., "--url"),
    out: Path = typer.Option(Path("artifacts/shot.png"), "--out"),
) -> None:
    """用 Playwright 截图（证据留存）。"""
    todo("screenshot", f"截图（{url} → {out}）", "TASK-0011", True)


@app.command()
def query(
    sql: str = typer.Option(..., "--sql"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """只读 SQL 查询（仅 SELECT/WITH）。"""
    todo("query", "只读 SQL", "TASK-0008", json_output)


@app.command()
def setup(json_output: bool = typer.Option(False, "--json")) -> None:
    """幂等地准备前端构建产物与本地数据目录。"""
    todo("setup", "初始化", "TASK-0002", json_output)


@app.command(name="format")
def format_all(json_output: bool = typer.Option(False, "--json")) -> None:
    """归一化 GeoJSON 文本（稳定排序、6 位小数）。"""
    todo("format", "格式化", "TASK-0010", json_output)


@app.command()
def export(
    static: bool = typer.Option(False, "--static"),
    qgis: bool = typer.Option(False, "--qgis"),
    out: Path = typer.Option(Path("dist"), "--out"),
) -> None:
    """导出（静态站点推迟到 M5 之后；QGIS 见 TASK-0010）。"""
    todo("export", f"导出（static={static}, qgis={qgis}, out={out}）", "TASK-0010", True)


@app.command()
def openapi(out: Path = typer.Option(Path("docs/openapi.json"), "--out")) -> None:
    """导出 OpenAPI 契约到文件。"""
    todo("openapi", f"导出 OpenAPI（{out}）", "TASK-0006", True)


@app.command()
def backup(out: Path = typer.Option(Path("backups"), "--out")) -> None:
    """备份：源码 + annotations.sql 打包。"""
    todo("backup", f"备份到 {out}", "TASK-0004", True)


@geometry_app.command("import")
def geo_import(directory: Path = typer.Option(..., "--dir")) -> None:
    """导入 QGIS 编辑后的几何目录。"""
    todo("geometry import", f"导入几何（{directory}）", "TASK-0010", True)


def run() -> None:
    """控制台入口；把领域异常映射为稳定退出码。"""
    try:
        app()
    except MapCreatorError as exc:
        typer.secho(json.dumps(exc.to_dict(), ensure_ascii=False), fg="red", err=True)
        sys.exit(exit_code_for(exc))


if __name__ == "__main__":  # pragma: no cover
    run()
