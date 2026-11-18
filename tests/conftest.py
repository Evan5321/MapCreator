"""pytest 全局夹具：仓库根、配置对象、mini-world 路径。

骨架阶段只提供路径级夹具，避免在依赖未安装时 import 第三方库。
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def mini_world() -> Path:
    path = REPO_ROOT / "tests" / "fixtures" / "mini-world"
    if not path.is_dir():
        pytest.skip("mini-world 夹具尚未创建（TASK-0003）")
    return path
