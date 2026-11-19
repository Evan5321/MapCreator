"""静态资源与 SPA 回退：`web/dist` 挂 `/`，`build/` 挂 `/map`。

缺失时给出可执行的修复提示，而不是 500。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ..errors import ConfigurationError


def mount(app: FastAPI, *, web_dist: Path, build_dir: Path) -> None:
    """挂载静态目录；`web/dist` 缺失即报错（前端未构建）。"""
    if not web_dist.is_dir():
        raise ConfigurationError(
            code="WEB_DIST_MISSING",
            message=f"前端产物不存在：{web_dist}",
            path=web_dist,
            remediation="在仓库根运行 `npm run build` 后重试",
        )
    if build_dir.is_dir():
        app.mount("/map", StaticFiles(directory=build_dir), name="map")
    app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
