"""GeoJSON 读写与校验。

职责：解析 FeatureCollection → 校验 id/kind/properties 白名单 → Shapely 有效性
      → 坐标 6 位小数归一化 → 稳定文本格式化。

不做：标注、样式、切分（分别在 data/annotations.py 与 build/）。
"""

from __future__ import annotations

from pathlib import Path

from ..config import KindDef
from ..models import GeometryFeature

TASK = "TASK-0005"


def load_layer(path: Path, *, allowed: set[str]) -> list[GeometryFeature]:
    """读取单个图层文件并做基础校验（白名单之外的键报错）。"""
    raise NotImplementedError(TASK)


def validate_geometry(feature: GeometryFeature, *, fix: bool = False) -> list[str]:
    """返回问题清单；fix=True 时尝试 make_valid 并记录警告。"""
    raise NotImplementedError(TASK)


def normalize(feature: GeometryFeature) -> GeometryFeature:
    """坐标 round(6)，去掉 -0.0，保持环方向。"""
    raise NotImplementedError(TASK)


def dump_layer(path: Path, features: list[GeometryFeature]) -> None:
    """写回：一个要素一行、稳定排序、固定缩进。"""
    raise NotImplementedError(TASK)


def kind_of(feature: GeometryFeature, kinds: dict[str, KindDef]) -> KindDef:
    """按 properties.kind 查注册表，未注册即报错。"""
    raise NotImplementedError(TASK)
