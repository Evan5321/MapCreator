"""CLI 公共输出与退出码。

契约（AGENTS.md §3）：所有命令支持 `--json`，输出
`ok / command / duration_ms / errors[] / warnings[] / artifacts[]`；
退出码 0 成功、1 数据失败、2 用法/配置错误、3 环境缺失、4 内部错误/未实现。
"""

from __future__ import annotations

import json
import time
from typing import Any, NoReturn

import typer

from . import __version__
from .errors import ConfigurationError, DataValidationError, EnvironmentError_, MapCreatorError

EXIT_OK = 0
EXIT_DATA = 1
EXIT_USAGE = 2
EXIT_ENV = 3
EXIT_INTERNAL = 4


def exit_code_for(exc: MapCreatorError) -> int:
    if isinstance(exc, ConfigurationError):
        return EXIT_USAGE
    if isinstance(exc, DataValidationError):
        return EXIT_DATA
    if isinstance(exc, EnvironmentError_):
        return EXIT_ENV
    return EXIT_INTERNAL


def finish(
    command: str,
    *,
    as_json: bool,
    started: float,
    errors: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    artifacts: list[str] | None = None,
    extra: dict[str, Any] | None = None,
    exit_code: int = EXIT_OK,
) -> NoReturn:
    """打印统一结果并退出。"""
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


def todo(command: str, feature: str, task: str, as_json: bool) -> NoReturn:
    """骨架阶段占位：统一产出可解析的 JSON，而不是 traceback。"""
    started = time.perf_counter()
    error = MapCreatorError(
        code="NOT_IMPLEMENTED",
        message=f"{feature} 尚未实现（{command}）",
        remediation=f"见 TODO.md 的 {task}",
        details={"task": task},
    ).to_dict()
    finish(command, as_json=as_json, started=started, errors=[error], exit_code=EXIT_INTERNAL)
