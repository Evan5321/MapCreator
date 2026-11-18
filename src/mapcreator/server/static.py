"""静态资源与 SPA 回退：web/dist + build/data，带缓存头。

注意：build/ 与 web/dist 都可能不存在；缺失时给出可执行的修复提示，
      而不是 500。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

TASK = "TASK-0006"


def mount(app: Any, *, web_dist: Path, build_dir: Path) -> None:
    """挂载静态目录与回退路由。"""
    raise NotImplementedError(TASK)
