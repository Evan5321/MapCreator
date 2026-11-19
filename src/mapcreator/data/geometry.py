"""GeoJSON 读写与校验。

职责：解析 FeatureCollection → 校验 id/kind/properties 白名单 → Shapely 有效性
      → 坐标 6 位小数归一化 → 稳定文本格式化。

不做：标注、样式、切分（分别在 data/annotations.py 与 build/）。
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from shapely.geometry import mapping, shape
from shapely.validation import explain_validity, make_valid

from ..config import KindDef
from ..errors import DataValidationError, data_error_from
from ..models import GeometryFeature

TASK = "TASK-0005"

# docs/DATA_SPEC.md §3：每个几何文件允许的 kind。layer.id 必须与 world.json 一致。
LAYER_KINDS: dict[str, frozenset[str]] = {
    "land": frozenset({"continent", "island"}),
    "water": frozenset({"ocean", "sea", "lake"}),
    "rivers": frozenset({"river", "canal"}),
    "terrain": frozenset({"mountain_range", "ridge"}),
    "roads": frozenset({"road", "street", "trail"}),
    "transit": frozenset({"metro", "bus", "rail"}),
    "parks": frozenset({"park", "reserve", "garden"}),
}

# docs/DATA_SPEC.md §3：每个几何文件允许的其他属性（kind 之外）。
LAYER_PROPERTIES: dict[str, frozenset[str]] = {
    "land": frozenset({"land_class"}),
    "water": frozenset({"water_class"}),
    "rivers": frozenset({"width_class"}),
    "terrain": frozenset({"elev_class"}),
    "roads": frozenset({"road_class", "surface"}),
    "transit": frozenset({"mode", "line_color"}),
    "parks": frozenset({"protected"}),
}


def load_layer(
    path: Path,
    *,
    allowed: frozenset[str],
    geometry_types: frozenset[str] | None = None,
    allowed_properties: frozenset[str] | None = None,
) -> list[GeometryFeature]:
    """读取单个图层文件并做基础校验（kind / 几何类型 / 属性白名单）。"""
    raw = _read_feature_collection(path)
    features: list[GeometryFeature] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        feature_id = item.get("id") if isinstance(item, dict) else None
        try:
            feature = GeometryFeature.model_validate(item)
        except ValidationError as exc:
            raise data_error_from(exc, path=path, feature_id=feature_id, index=index) from exc

        if feature.id in seen:
            raise DataValidationError(
                code="DUPLICATE_FEATURE_ID",
                message=f"{path.name}: 重复的要素 ID {feature.id}",
                path=path,
                feature_id=feature.id,
                remediation="每个要素 ID 必须全局唯一",
            )
        seen.add(feature.id)

        kind = feature.properties["kind"]
        if kind not in allowed:
            raise DataValidationError(
                code="KIND_NOT_ALLOWED",
                message=f"{path.name}: 要素 {feature.id} 的 kind={kind!r} 不属于该图层",
                path=path,
                feature_id=feature.id,
                remediation=f"允许的 kind：{sorted(allowed)}",
            )
        if geometry_types is not None and feature.geometry_type not in geometry_types:
            raise DataValidationError(
                code="GEOMETRY_TYPE_NOT_ALLOWED",
                message=(
                    f"{path.name}: 要素 {feature.id} 的几何类型 "
                    f"{feature.geometry_type!r} 不属于该图层"
                ),
                path=path,
                feature_id=feature.id,
                remediation=f"允许的几何类型：{sorted(geometry_types)}",
            )
        if allowed_properties is not None:
            extra = set(feature.properties) - {"kind"} - allowed_properties
            if extra:
                raise DataValidationError(
                    code="PROPERTY_NOT_ALLOWED",
                    message=f"{path.name}: 要素 {feature.id} 含白名单之外的属性 {sorted(extra)}",
                    path=path,
                    feature_id=feature.id,
                    remediation=(
                        f"允许的属性：{sorted(allowed_properties)}；"
                        "名称/等级等标注语义请写入 annotations，而不是 GeoJSON"
                    ),
                )
        features.append(feature)
    return features


def _read_feature_collection(path: Path) -> list[Any]:
    if not path.is_file():
        raise DataValidationError(
            code="GEOMETRY_MISSING",
            message=f"几何文件不存在：{path.name}",
            path=path,
            remediation="确认 world/world.json 的 layers 与本目录文件一致",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DataValidationError(
            code="GEOMETRY_INVALID_JSON",
            message=f"{path.name}: JSON 解析失败：{exc.msg}（第 {exc.lineno} 行）",
            path=path,
            remediation="用 `mapcreator format` 或手工修复该文件的 JSON 语法",
        ) from exc
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise DataValidationError(
            code="GEOMETRY_INVALID_ROOT",
            message=f"{path.name}: 根对象必须是 FeatureCollection",
            path=path,
            remediation='把文件写成 {"type": "FeatureCollection", "features": [...]}',
        )
    features = payload.get("features")
    if not isinstance(features, list):
        raise DataValidationError(
            code="GEOMETRY_INVALID_ROOT",
            message=f"{path.name}: features 必须是数组",
            path=path,
            remediation='补上 "features": []（可以为空）',
        )
    return features


def iter_points(feature: GeometryFeature) -> Iterator[tuple[float, float]]:
    """遍历要素内的全部 [lon, lat] 坐标（忽略可选高程）。"""
    coordinates = feature.geometry.get("coordinates")
    yield from _walk_coordinates(coordinates)


def _walk_coordinates(value: Any) -> Iterator[tuple[float, float]]:
    if not isinstance(value, list):
        return
    if len(value) >= 2 and all(isinstance(item, (int, float)) for item in value):
        yield float(value[0]), float(value[1])
        return
    for item in value:
        yield from _walk_coordinates(item)


def round_coord(value: float) -> float:
    """6 位小数并去掉 -0.0（docs/DATA_SPEC.md §1）。"""
    rounded = round(value, 6)
    return 0.0 if rounded == 0 else rounded


def validate_geometry(feature: GeometryFeature, *, fix: bool = False) -> list[str]:
    """用 Shapely 检查几何有效性；返回问题清单（空表示通过）。

    fix=True 时尝试 `make_valid` 修好当前对象（调用方须记录警告）。
    """
    geometry = _to_shapely(feature)
    if geometry.is_valid:
        return []
    problems = [f"{feature.id}: {explain_validity(geometry)}"]
    if fix:
        feature.geometry = mapping(make_valid(geometry))
    return problems


def normalize(feature: GeometryFeature) -> GeometryFeature:
    """坐标 round(6)、去掉 -0.0，保持环方向（docs/DATA_SPEC.md §1）。"""
    return feature.model_copy(update={"geometry": normalize_coordinates(feature.geometry)})


def normalize_coordinates(geometry: dict[str, Any]) -> dict[str, Any]:
    """递归归一化 GeoJSON geometry 的 coordinates。"""
    result = dict(geometry)
    if "coordinates" in result:
        result["coordinates"] = _round_value(result["coordinates"])
    members = result.get("geometries")
    if isinstance(members, list):
        result["geometries"] = [normalize_coordinates(item) for item in members]
    return result


def _round_value(value: Any) -> Any:
    if isinstance(value, list):
        return [_round_value(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round_coord(float(value))
    return value


def _to_shapely(feature: GeometryFeature) -> Any:
    try:
        return shape(feature.geometry)
    except (ValueError, TypeError) as exc:
        raise DataValidationError(
            code="GEOMETRY_UNREADABLE",
            message=f"要素 {feature.id} 的几何无法解析：{exc}",
            feature_id=feature.id,
            remediation="检查 geometry.type 与 coordinates 的结构",
        ) from exc


def dump_layer(path: Path, features: list[GeometryFeature]) -> None:
    """写回：一个要素一行、稳定排序、固定缩进（TASK-0005）。"""
    raise NotImplementedError(TASK)


def kind_of(feature: GeometryFeature, kinds: dict[str, KindDef]) -> KindDef:
    """按 properties.kind 查注册表，未注册即报错。"""
    kind_name = str(feature.properties["kind"])
    kind = kinds.get(kind_name)
    if kind is None:
        raise DataValidationError(
            code="KIND_NOT_REGISTERED",
            message=f"要素 {feature.id} 的 kind={kind_name!r} 未在 config/kinds.toml 注册",
            feature_id=feature.id,
            remediation="在 kinds.toml 注册该 kind（并补 schema/图标/颜色 token）",
        )
    return kind
