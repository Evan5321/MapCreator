"""环境自检（doctor）：只读探测，不安装、不联网。

契约见 AGENTS.md §3 与 docs/ENVIRONMENT.md §9：
- `required=True` 的项缺失 → 退出码 3（环境缺失）；
- 每一项都必须给出可执行的 `remediation`；
- 输出可被脚本消费（`--json`）。
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Status = Literal["ok", "warn", "missing"]
WhichFn = Callable[[str], str | None]
RunFn = Callable[[list[str]], str | None]

MIN_PYTHON = (3, 12)
MIN_NODE = (20, 0)
MIN_SQLITE = (3, 34)


@dataclass(slots=True)
class Check:
    """单项检查结果；`value` 是给人看的一行摘要。"""

    name: str
    status: Status
    value: str
    required: bool = True
    remediation: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "required": self.required,
            "value": self.value,
            "remediation": self.remediation,
        }


def default_run(args: list[str]) -> str | None:
    """执行只读版本命令；失败返回 None（不抛异常，doctor 不应崩溃）。"""
    command = list(args)
    resolved = shutil.which(args[0])
    # npm 之类在 Windows 上是 .cmd 包装脚本，CreateProcess 不能直接执行。
    if sys.platform == "win32" and resolved and resolved.lower().endswith((".cmd", ".bat")):
        command = ["cmd", "/c", *args]
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    text = (proc.stdout or proc.stderr).strip()
    return text.splitlines()[0] if text else None


def _version_tuple(text: str) -> tuple[int, ...]:
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    if not match:
        return ()
    return tuple(int(part) for part in match.groups() if part is not None)


def _tool_check(
    name: str,
    args: Sequence[str],
    *,
    minimum: tuple[int, ...] | None,
    remediation: str,
    required: bool = True,
    which: WhichFn = shutil.which,
    run: RunFn = default_run,
) -> Check:
    path = which(name)
    if path is None:
        return Check(name, "missing", "未找到可执行文件", required, remediation)
    output = run([name, *args])
    if output is None:
        return Check(name, "warn", f"{path}（无法获取版本）", required, remediation)
    if minimum is not None and _version_tuple(output) < minimum:
        need = ".".join(str(part) for part in minimum)
        return Check(name, "missing", f"{output} < {need}（{path}）", required, remediation)
    return Check(name, "ok", f"{output}（{path}）", required)


def check_python() -> Check:
    version = sys.version.split()[0]
    ok = sys.version_info >= MIN_PYTHON
    return Check(
        "python",
        "ok" if ok else "missing",
        f"{version}（{sys.executable}）",
        True,
        None
        if ok
        else "安装 Python 3.12+：https://www.python.org/downloads/windows/，"
        "然后重跑 scripts/install-deps.ps1",
    )


def probe_sqlite() -> dict[str, bool]:
    """探测 SQLite 能力：FTS5 / RTree / trigram tokenizer。"""
    caps = {"fts5": False, "rtree": False, "trigram": False}
    conn = sqlite3.connect(":memory:")
    try:
        for key, ddl in (
            ("fts5", "CREATE VIRTUAL TABLE probe_fts USING fts5(content)"),
            ("rtree", "CREATE VIRTUAL TABLE probe_rtree USING rtree(id, minx, maxx)"),
            (
                "trigram",
                "CREATE VIRTUAL TABLE probe_tri USING fts5(content, tokenize='trigram')",
            ),
        ):
            try:
                conn.execute(ddl)
                caps[key] = True
            except sqlite3.Error:
                caps[key] = False
    finally:
        conn.close()
    return caps


def check_sqlite() -> Check:
    caps = probe_sqlite()
    version = sqlite3.sqlite_version
    missing = [name for name, ok in caps.items() if not ok]
    too_old = _version_tuple(version) < MIN_SQLITE
    if too_old or missing:
        detail = "、".join(missing) if missing else "版本 < 3.34"
        return Check(
            "sqlite",
            "missing",
            f"{version}，缺少：{detail}",
            True,
            "使用 Python 3.12+ 官方安装包（自带开启 FTS5/RTree/trigram 的 SQLite），"
            "不要用第三方精简版 sqlite3.dll",
        )
    return Check("sqlite", "ok", f"{version}（FTS5/RTree/trigram 可用）", True)


def playwright_browsers_dir() -> Path:
    """与 Playwright 默认规则一致，额外支持自定义 PLAYWRIGHT_BROWSERS_PATH。"""
    custom = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if custom and custom != "0":
        return Path(custom)
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


def check_playwright() -> Check:
    if importlib.util.find_spec("playwright") is None:
        return Check(
            "playwright",
            "missing",
            "Python 包未安装",
            False,
            "运行 scripts/install-deps.ps1（会执行 uv sync）",
        )
    directory = playwright_browsers_dir()
    if not directory.is_dir():
        return Check(
            "playwright",
            "missing",
            f"未找到浏览器目录 {directory}",
            False,
            "执行 `uv run playwright install chromium`；"
            f"若目录不可写，请把 {directory} 加入 Trae 的文件写权限或改 PLAYWRIGHT_BROWSERS_PATH",
        )
    has_chromium = any(
        child.is_dir() and child.name.startswith("chromium") for child in directory.iterdir()
    )
    if not has_chromium:
        return Check(
            "playwright",
            "missing",
            f"{directory} 中没有 chromium-*",
            False,
            "执行 `uv run playwright install chromium`",
        )
    return Check("playwright", "ok", f"chromium 已就绪（{directory}）", False)


def collect_checks(
    *,
    which: WhichFn = shutil.which,
    run: RunFn = default_run,
) -> list[Check]:
    """按 ENVIRONMENT.md 的顺序收集全部检查项。"""
    checks = [
        check_python(),
        _tool_check(
            "uv",
            ["--version"],
            minimum=None,
            remediation="安装 uv：https://docs.astral.sh/uv/getting-started/installation/",
            which=which,
            run=run,
        ),
        _tool_check(
            "node",
            ["--version"],
            minimum=MIN_NODE,
            remediation="安装 Node.js 20 LTS+：https://nodejs.org/zh-cn/download",
            which=which,
            run=run,
        ),
        _tool_check(
            "npm",
            ["--version"],
            minimum=None,
            remediation="npm 随 Node.js 安装；确认 PATH 中存在 npm",
            which=which,
            run=run,
        ),
        _tool_check(
            "git",
            ["--version"],
            minimum=None,
            remediation="安装 Git：https://git-scm.com/download/win",
            which=which,
            run=run,
        ),
        check_sqlite(),
        check_playwright(),
    ]
    optional = (
        ("pwsh", ["-v"], "可选：安装 PowerShell 7 以使用 scripts/install-deps.ps1 的原生调用"),
        ("qgis", ["--version"], "可选：QGIS 3.34+ 用于批量/拓扑编辑（仅外部工具）"),
        ("docker", ["--version"], "可选：后续 tippecanoe 切片需要 Docker 或 WSL"),
        ("tippecanoe", ["--version"], "可选：后续瓦片生成，建议在 WSL/Docker 中使用"),
    )
    for name, args, hint in optional:
        checks.append(
            _tool_check(
                name,
                args,
                minimum=None,
                remediation=hint,
                required=False,
                which=which,
                run=run,
            )
        )
    return checks


def render_lines(checks: Sequence[Check]) -> list[str]:
    """人类可读的逐项输出；缺失/告警项附带修复建议。"""
    marks: dict[Status, str] = {"ok": "✓", "warn": "!", "missing": "✗"}
    lines: list[str] = []
    for check in checks:
        lines.append(f"{marks[check.status]} {check.name}: {check.value}")
        if check.status != "ok" and check.remediation:
            lines.append(f"    → {check.remediation}")
    return lines
