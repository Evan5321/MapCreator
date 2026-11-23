"""按缩放带切分与简化。

带边界**只**来自 config/zoom_bands.toml（D-018）；kind 的 zoom 区间只产生
style filter，不参与切分。
"""

from __future__ import annotations

from typing import Any

from shapely.geometry import mapping, shape

from ..config import AppConfig, BandDef, KindDef
from ..data.geometry import normalize_coordinates
from ..models import Annotation

TASK = "TASK-0006"
MAX_LABELS_PER_BAND = 3000


def bands_for(config: AppConfig, min_zoom: float, max_zoom: float) -> list[BandDef]:
    """返回与该 zoom 区间有交集的带（按 min_zoom 升序）。"""
    return [
        band
        for band in sorted(config.bands, key=lambda item: item.min_zoom)
        if band.min_zoom <= max_zoom and band.max_zoom >= min_zoom
    ]


def resolved_zoom(annotation: Annotation, kind: KindDef) -> tuple[float, float]:
    """标注的最终 zoom 区间：标注覆盖优先，否则取 kind 默认值（**不回写库**）。"""
    min_zoom = annotation.min_zoom if annotation.min_zoom is not None else kind.default_min_zoom
    max_zoom = annotation.max_zoom if annotation.max_zoom is not None else kind.default_max_zoom
    return min_zoom, max_zoom


def labels_for_band(
    config: AppConfig,
    annotations: list[Annotation],
    band: BandDef,
) -> list[Annotation]:
    """该带可见的标注（含默认 zoom 回填；label_mode=none 不参与）。

    按 (rank, id) 稳定排序，超出 3000 条时裁掉低 rank。
    """
    visible: list[Annotation] = []
    for annotation in annotations:
        if annotation.label_mode == "none":
            continue
        kind = config.kinds.get(annotation.kind)
        if kind is None:
            continue
        min_zoom, max_zoom = resolved_zoom(annotation, kind)
        if min_zoom <= band.max_zoom and max_zoom >= band.min_zoom:
            visible.append(annotation)
    visible.sort(key=lambda item: (item.rank, item.id))
    return visible


def label_name(annotation: Annotation, default_lang: str) -> str:
    """渲染分片里的显示名：默认语种优先，其次主名。"""
    for item in annotation.names:
        if item.lang == default_lang and item.is_primary:
            return item.name
    for item in annotation.names:
        if item.lang == default_lang:
            return item.name
    primary = annotation.primary_name
    return primary.name if primary is not None else ""


def simplify_geometry(geometry: dict[str, Any], tolerance: float) -> dict[str, Any]:
    """shapely.simplify(tol, preserve_topology=True)；tolerance=0 时原样返回。"""
    if tolerance <= 0:
        return normalize_coordinates(geometry)
    simplified = shape(geometry).simplify(tolerance, preserve_topology=True)
    return normalize_coordinates(mapping(simplified))
