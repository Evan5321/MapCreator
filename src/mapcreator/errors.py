"""统一异常：所有对外错误都必须能定位到文件/要素，并给出修复建议。

契约见 docs/DATA_SPEC.md §9 与 AGENTS.md §6：错误体包含
`code / message / path / feature_id / details / remediation`。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError


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


def _issues(exc: ValidationError) -> list[dict[str, Any]]:
    """把 pydantic 错误压平成可序列化的 `loc/msg/type` 清单。"""
    return [
        {
            "loc": ".".join(str(part) for part in err["loc"]),
            "msg": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors(include_url=False)
    ]


def config_error_from(exc: ValidationError, path: Path) -> ConfigurationError:
    """配置模型校验失败 → 带**字段路径**的 ConfigurationError（退出码 2）。"""
    issues = _issues(exc)
    first = issues[0] if issues else {"loc": "", "msg": "校验失败"}
    return ConfigurationError(
        code="CONFIG_INVALID",
        message=f"{path.name}:{first['loc']}: {first['msg']}",
        path=path,
        remediation="按 docs/DATA_SPEC.md 与本文件注释修正该字段",
        details={"issues": issues},
    )


def data_error_from(
    exc: ValidationError,
    *,
    path: Path,
    feature_id: str | None = None,
    index: int | None = None,
) -> DataValidationError:
    """数据模型校验失败 → 带文件、要素 ID 与字段路径的 DataValidationError（退出码 1）。"""
    issues = _issues(exc)
    first = issues[0] if issues else {"loc": "", "msg": "校验失败"}
    location = path.name if index is None else f"{path.name}#{index}"
    return DataValidationError(
        code="SCHEMA_INVALID",
        message=f"{location}:{first['loc']}: {first['msg']}",
        path=path,
        feature_id=feature_id,
        remediation="按 docs/DATA_SPEC.md 与 schemas/ 修正该要素",
        details={"issues": issues, "index": index},
    )
