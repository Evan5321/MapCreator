"""统一异常：所有对外错误都必须能定位到文件/要素，并给出修复建议。

契约见 docs/DATA_SPEC.md §9 与 AGENTS.md §6：错误体包含
`code / message / path / feature_id / details / remediation`。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class MapCreatorError(Exception):
    """可序列化的领域异常。CLI 与 API 共用同一形态。"""

    code: str
    message: str
    path: Path | str | None = None
    feature_id: str | None = None
    remediation: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "path": None if self.path is None else str(self.path).replace("\\", "/"),
            "feature_id": self.feature_id,
            "details": self.details,
            "remediation": self.remediation,
        }


class ConfigurationError(MapCreatorError):
    """配置缺失/非法（退出码 2）。"""


class EnvironmentError_(MapCreatorError):
    """运行环境不满足要求（退出码 3）。名字带下划线以避免遮蔽内建 EnvironmentError。"""


class DataValidationError(MapCreatorError):
    """数据校验失败（退出码 1）。"""


class NotImplementedYet(MapCreatorError):
    """骨架阶段的占位：功能尚未实现，指向对应任务。"""

    def __init__(self, feature: str, task: str) -> None:
        super().__init__(
            code="NOT_IMPLEMENTED",
            message=f"{feature} 尚未实现",
            remediation=f"查看 TODO.md 中的 {task}",
            details={"feature": feature, "task": task},
        )
