"""E2E：页面加载、地图就绪、缩放带切换。

骨架阶段跳过；需要 Playwright 与浏览器（TASK-0011）。
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="TASK-0011 接入 Playwright 后启用")
def test_page_ready() -> None:
    assert True
