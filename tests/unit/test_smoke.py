"""最小冒烟：包可导入、版本号存在。

不依赖任何第三方库，保证 `pytest tests/unit` 在只装了 pytest 的环境也能跑。
"""

from __future__ import annotations

import mapcreator


def test_version() -> None:
    assert mapcreator.__version__
    assert mapcreator.__version__.count(".") >= 1
