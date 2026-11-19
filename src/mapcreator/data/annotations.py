"""标注与多语言名称的加载、校验、归一化。

约束：名称必有一个主名；点标注 geometry_id 恒为 NULL（D-015）；
      attrs 受 kind 的 attrs_schema 约束。

数据来源（按优先级）：
1. `<data_root>/annotations.json`：测试夹具与早期导入快照；
2. `<data_root>/annotations.db`：M0 之后的 SQLite 工作库（TASK-0004 接入）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..errors import DataValidationError, data_error_from
from ..models import Annotation

TASK = "TASK-0004"


def load_export(path: Path) -> list[Annotation]:
    """读取 annotations.json / annotations.export.json。

    接受 `{"annotations": [...]}` 或裸数组两种形态。
    """
    if not path.is_file():
        raise DataValidationError(
            code="ANNOTATIONS_MISSING",
            message=f"标注文件不存在：{path.name}",
            path=path,
            remediation="先用 `mapcreator db dump` 生成，或检查 --root 指向的目录",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DataValidationError(
            code="ANNOTATIONS_INVALID_JSON",
            message=f"{path.name}: JSON 解析失败：{exc.msg}（第 {exc.lineno} 行）",
            path=path,
            remediation="修复该文件的 JSON 语法后重试",
        ) from exc

    items = payload.get("annotations") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise DataValidationError(
            code="ANNOTATIONS_INVALID_ROOT",
            message=f"{path.name}: 必须是数组，或含 annotations 数组的对象",
            path=path,
            remediation='写成 {"annotations": [...]} 或 [...]',
        )

    annotations: list[Annotation] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        annotation_id = item.get("id") if isinstance(item, dict) else None
        try:
            annotation = Annotation.model_validate(item)
        except ValidationError as exc:
            raise data_error_from(exc, path=path, feature_id=annotation_id, index=index) from exc
        if annotation.id in seen:
            raise DataValidationError(
                code="DUPLICATE_ANNOTATION_ID",
                message=f"{path.name}: 重复的标注 ID {annotation.id}",
                path=path,
                feature_id=annotation.id,
                remediation="标注 ID 必须全局唯一（anno.<kind>.<slug>）",
            )
        seen.add(annotation.id)
        annotations.append(annotation)
    return annotations


def load_annotations(data_root: Path) -> list[Annotation]:
    """按优先级读取数据目录中的标注；都没有则视为空世界。"""
    exported = data_root / "annotations.json"
    if exported.is_file():
        return load_export(exported)
    database = data_root / "annotations.db"
    if database.is_file():
        return _load_from_database(database)
    return []


def _load_from_database(path: Path) -> list[Annotation]:
    """从工作库读取标注：只经 `db/repo.py` 这一条读取路径。"""
    from ..db import repo

    conn = repo.connect(path)
    try:
        rows = repo.export_annotations(conn)
    finally:
        conn.close()

    annotations: list[Annotation] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        annotation_id = row.get("id") if isinstance(row, dict) else None
        try:
            annotation = Annotation.model_validate(row)
        except ValidationError as exc:
            raise data_error_from(exc, path=path, feature_id=annotation_id, index=index) from exc
        if annotation.id in seen:
            raise DataValidationError(
                code="DUPLICATE_ANNOTATION_ID",
                message=f"{path.name}: 重复的标注 ID {annotation.id}",
                path=path,
                feature_id=annotation.id,
                remediation="检查工作库中的 annotation 表主键",
            )
        seen.add(annotation.id)
        annotations.append(annotation)
    return annotations


def validate_annotation(annotation: Annotation, *, kinds: dict[str, Any]) -> list[str]:
    """返回问题清单（引用完整性、kind 合法性、主名、zoom 区间）。"""
    raise NotImplementedError(TASK)


def normalize(annotation: Annotation) -> Annotation:
    """坐标 6 位小数；名称按 (lang, role) 稳定排序。"""
    raise NotImplementedError(TASK)


def to_export(annotation: Annotation) -> dict[str, Any]:
    """导出为 AI/人类友好的 JSON 形态。"""
    raise NotImplementedError(TASK)
