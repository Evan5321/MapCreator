"""API 端点（契约见 docs/ARCHITECTURE.md §6）。

GET  /api/health, /api/world, /api/data/{band}
GET  /api/annotations/{id}, /api/search, /api/map/{bbox}
POST /api/query（--enable-sql）
POST/PATCH/DELETE /api/annotations, /api/geometry（--enable-edit）
"""

from __future__ import annotations

from typing import Any

TASK = "TASK-0006"


def register_routes(app: Any, *, enable_edit: bool, enable_sql: bool) -> None:
    """把端点挂到应用上；按模式决定注册哪些。"""
    raise NotImplementedError(TASK)
