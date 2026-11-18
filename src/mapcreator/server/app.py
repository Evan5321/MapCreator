"""FastAPI 应用装配与运行模式开关。

模式：只读（默认）/ 编辑（--enable-edit）/ 只读 SQL（--enable-sql）/ dev（--dev）。
安全：校验 Origin/Host；默认只绑 127.0.0.1；编辑端点未开启时返回 404。
"""

from __future__ import annotations

from typing import Any

TASK = "TASK-0006"


def create_app(*, enable_edit: bool = False, enable_sql: bool = False, dev: bool = False) -> Any:
    """构建应用实例（不在导入期创建全局 app）。"""
    raise NotImplementedError(TASK)


def run(host: str, port: int, **options: bool) -> None:
    """启动 uvicorn（单 worker）。"""
    raise NotImplementedError(TASK)
