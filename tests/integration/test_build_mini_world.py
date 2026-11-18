"""集成：mini-world 全量构建。

骨架阶段跳过；实现见 TASK-0005。
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="TASK-0005 实现构建管线后启用")
def test_build_produces_manifest() -> None:
    assert True
