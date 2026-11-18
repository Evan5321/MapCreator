"""标注与多语言名称的加载、校验、归一化。

约束：名称必有一个主名；点标注 geometry_id 恒为 NULL（D-015）；
      attrs 受 kind 的 attrs_schema 约束。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import Annotation

TASK = "TASK-0004"


def load_export(path: Path) -> list[Annotation]:
    """读取 annotations.export.json。"""
    raise NotImplementedError(TASK)


def validate_annotation(annotation: Annotation, *, kinds: dict[str, Any]) -> list[str]:
    """返回问题清单（引用完整性、kind 合法性、主名、zoom 区间）。"""
    raise NotImplementedError(TASK)


def normalize(annotation: Annotation) -> Annotation:
    """坐标 6 位小数；名称按 (lang, role) 稳定排序。"""
    raise NotImplementedError(TASK)


def to_export(annotation: Annotation) -> dict[str, Any]:
    """导出为 AI/人类友好的 JSON 形态。"""
    raise NotImplementedError(TASK)
