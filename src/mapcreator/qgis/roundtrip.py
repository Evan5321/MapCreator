"""QGIS 导出/导入。

要点：QGIS 会重排 GeoJSON 文本，导入后必须 format；往返不得丢 attrs/names；
     QGIS 是 GPL 外部工具，不链接、不捆绑。
"""

from __future__ import annotations

from pathlib import Path

from ..config import AppConfig

TASK = "TASK-0010"


def export(config: AppConfig, out_dir: Path) -> dict[str, Path]:
    """导出 geometry/*.geojson 与 annotations.geojson。"""
    raise NotImplementedError(TASK)


def import_geometry(config: AppConfig, directory: Path) -> int:
    """导入编辑后的几何，返回变更要素数。"""
    raise NotImplementedError(TASK)


def import_annotations(config: AppConfig, path: Path) -> int:
    """导入编辑后的标注，返回变更行数。"""
    raise NotImplementedError(TASK)
