"""世界数据装配：world.json + 几何图层 + 标注 → 概览 / 供构建复用。

`describe` 只读；任何不一致都必须以 DataValidationError 报出文件与要素 ID。
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..config import AppConfig
from ..errors import DataValidationError, data_error_from
from ..models import Annotation, GeometryFeature, WorldDocument
from .annotations import load_annotations
from .geometry import (
    LAYER_KINDS,
    LAYER_PROPERTIES,
    iter_points,
    load_layer,
    round_coord,
)


def load_world(data_root: Path) -> WorldDocument:
    """读取并校验 `<data_root>/world.json`。"""
    path = data_root / "world.json"
    if not path.is_file():
        raise DataValidationError(
            code="WORLD_MISSING",
            message=f"世界清单不存在：{path}",
            path=path,
            remediation="确认 --root 指向的目录含 world.json，或先生成默认骨架",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DataValidationError(
            code="WORLD_INVALID_JSON",
            message=f"{path.name}: JSON 解析失败：{exc.msg}（第 {exc.lineno} 行）",
            path=path,
            remediation="修复 world.json 的 JSON 语法",
        ) from exc
    try:
        return WorldDocument.model_validate(payload)
    except ValidationError as exc:
        raise data_error_from(exc, path=path) from exc


def load_features(data_root: Path, document: WorldDocument) -> dict[str, list[GeometryFeature]]:
    """按图层清单读取全部几何，并检查 layer.id 已注册、ID 全局唯一。"""
    root = data_root.resolve()
    layers: dict[str, list[GeometryFeature]] = {}
    seen: dict[str, str] = {}
    for layer in document.layers:
        allowed = LAYER_KINDS.get(layer.id)
        if allowed is None:
            raise DataValidationError(
                code="LAYER_NOT_REGISTERED",
                message=f"world.json: 图层 id {layer.id!r} 未在数据规范中注册",
                path=data_root / "world.json",
                remediation=f"使用 DATA_SPEC §3 的图层名：{sorted(LAYER_KINDS)}",
            )
        path = (data_root / layer.file).resolve()
        if not path.is_relative_to(root):
            raise DataValidationError(
                code="LAYER_OUTSIDE_WORLD",
                message=f"world.json: 图层 {layer.id} 的文件越出世界目录",
                path=data_root / "world.json",
                remediation="layer.file 必须是 world 目录内的相对路径",
            )
        features = load_layer(
            path,
            allowed=allowed,
            geometry_types=frozenset(layer.geometry),
            allowed_properties=LAYER_PROPERTIES[layer.id],
        )
        for feature in features:
            previous = seen.get(feature.id)
            if previous is not None:
                raise DataValidationError(
                    code="DUPLICATE_FEATURE_ID",
                    message=f"要素 ID {feature.id} 同时出现在 {previous} 与 {layer.id}",
                    path=path,
                    feature_id=feature.id,
                    remediation="几何 ID 必须全局唯一",
                )
            seen[feature.id] = layer.id
        layers[layer.id] = features
    return layers


def derive_bounds(
    config: AppConfig,
    features: list[GeometryFeature],
    annotations: list[Annotation],
) -> list[float] | None:
    """推导世界 bounds：world.toml 覆盖优先，否则按数据外扩 padding。"""
    if config.world.bounds is not None:
        return [round_coord(value) for value in config.world.bounds]

    lons: list[float] = []
    lats: list[float] = []
    for feature in features:
        for lon, lat in iter_points(feature):
            lons.append(lon)
            lats.append(lat)
    for annotation in annotations:
        lons.append(annotation.lon)
        lats.append(annotation.lat)
    if not lons:
        return None

    padding = config.world.bounds_padding
    return [
        round_coord(max(-180.0, min(lons) - padding)),
        round_coord(max(-90.0, min(lats) - padding)),
        round_coord(min(180.0, max(lons) + padding)),
        round_coord(min(90.0, max(lats) + padding)),
    ]


def describe_world(config: AppConfig, data_root: Path) -> dict[str, Any]:
    """世界概览：bounds、计数、kind 清单、缩放带。"""
    document = load_world(data_root)
    if document.world.id != config.world.id:
        raise DataValidationError(
            code="WORLD_ID_MISMATCH",
            message=(
                f"world.json 的 world.id={document.world.id!r} "
                f"与 config/world.toml 的 {config.world.id!r} 不一致"
            ),
            path=data_root / "world.json",
            remediation="让两处 world.id 一致（ID 是契约，确定后不再改）",
        )
    layers = load_features(data_root, document)
    annotations = load_annotations(data_root)

    flat = [feature for features in layers.values() for feature in features]
    geometry_kinds = Counter(str(feature.properties["kind"]) for feature in flat)
    annotation_kinds = Counter(annotation.kind for annotation in annotations)
    # 几何 kind 由 LAYER_KINDS 校验；config/kinds.toml 管的是标注 kind。
    unregistered = sorted(kind for kind in annotation_kinds if kind not in config.kinds)
    if unregistered:
        raise DataValidationError(
            code="KIND_NOT_REGISTERED",
            message=f"标注中使用了未注册的 kind：{unregistered}",
            path=data_root / "annotations.json",
            remediation="在 config/kinds.toml 注册，或修正数据中的 kind",
        )

    return {
        "world": {
            "id": document.world.id,
            "name": document.world.name,
            "default_lang": document.world.default_lang,
            "schema_version": document.schema_version,
        },
        "bounds": derive_bounds(config, flat, annotations),
        "counts": {
            "geometry_total": len(flat),
            "annotation_total": len(annotations),
            "by_layer": {layer.id: len(layers.get(layer.id, [])) for layer in document.layers},
            "geometry_kinds": dict(sorted(geometry_kinds.items())),
            "annotation_kinds": dict(sorted(annotation_kinds.items())),
        },
        "bands": [
            {"name": band.name, "min_zoom": band.min_zoom, "max_zoom": band.max_zoom}
            for band in sorted(config.bands, key=lambda item: item.min_zoom)
        ],
        "kinds": sorted(config.kinds),
    }
