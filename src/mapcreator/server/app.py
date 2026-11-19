"""FastAPI 应用装配与运行模式开关。

模式：只读（默认）/ 编辑（--enable-edit）/ 只读 SQL（--enable-sql）/ dev（--dev）。
安全：默认只绑 127.0.0.1；编辑/SQL 端点未开启时不注册。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI

from .. import __version__
from ..config import load_config
from . import static
from .routes import register_routes


def create_app(
    *,
    enable_edit: bool = False,
    enable_sql: bool = False,
    dev: bool = False,
    root: Path | None = None,
    build_dir: Path | None = None,
    web_dist: Path | None = None,
    db_path: Path | None = None,
) -> FastAPI:
    """构建应用实例（不在导入期创建全局 app）。"""
    config = load_config(root)
    app = FastAPI(
        title="MapCreator",
        version=__version__,
        docs_url="/api/docs" if dev else None,
        redoc_url=None,
    )
    register_routes(
        app,
        config=config,
        build_dir=build_dir or config.root / "build",
        db_path=db_path or config.root / "world" / "annotations.db",
        enable_edit=enable_edit,
        enable_sql=enable_sql,
    )
    static.mount(
        app,
        web_dist=web_dist or config.root / "web" / "dist",
        build_dir=build_dir or config.root / "build",
    )
    return app


def run(host: str, port: int, **options: Any) -> None:
    """启动 uvicorn（单 worker，默认仅本机）。"""
    import uvicorn

    uvicorn.run(create_app(**options), host=host, port=port, log_level="info")
