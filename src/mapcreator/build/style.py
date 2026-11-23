"""样式生成：`styles/base.maplibre.json` + palette/kind → `build/style.json`。

约束：
- 颜色/字号只来自 `config/palette.toml`，不在这里硬编码。
- 地图容器里没有字体 glyph 与 icon sprite（未引入资产），因此**文字标签由前端 DOM 渲染**，
  样式里只生成底图与几何/点符号图层。
- 输出确定性：稳定键序由 `pipeline._write_json` 保证。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import AppConfig
from ..errors import ConfigurationError


def load_base(root: Path) -> dict[str, Any]:
    """读取手工维护的底图样式。"""
    path = root / "styles" / "base.maplibre.json"
    if not path.is_file():
        raise ConfigurationError(
            code="STYLE_BASE_MISSING",
            message=f"底图样式不存在：{path.name}",
            path=path,
            remediation="恢复 styles/base.maplibre.json（它不是生成物）",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            code="STYLE_BASE_INVALID",
            message=f"{path.name}: JSON 解析失败：{exc.msg}（第 {exc.lineno} 行）",
            path=path,
            remediation="修正该文件后重试",
        ) from exc
    if not isinstance(payload, dict):
        raise ConfigurationError(
            code="STYLE_BASE_INVALID",
            message=f"{path.name}: 根对象必须是 JSON 对象",
            path=path,
            remediation="修正该文件后重试",
        )
    return payload


def generate(config: AppConfig) -> dict[str, Any]:
    """生成 MapLibre style（version 8）。"""
    style = load_base(config.root)
    surface = config.palette.surface
    line = config.palette.line
    transit = config.palette.transit

    style["metadata"] = {
        "mapcreator:kind": "generated",
        "mapcreator:note": "由 `mapcreator build` 生成，请勿手工编辑",
    }
    # 当前没有 symbol/text 图层（标签由前端 DOM 渲染），去掉 base 里的 glyphs 以免请求不存在的字体。
    style.pop("glyphs", None)
    style["sources"] = {
        "geometry": {"type": "geojson", "data": "unified.geojson"},
    }
    style["layers"] = [
        _background(surface.background),
        _fill("land", "land", surface.land),
        _outline("land", "land", surface.land_border),
        _fill("water", "water", surface.water),
        _outline("water", "water", surface.water_border),
        _fill("parks", "parks", surface.park),
        _fill("terrain", "terrain", surface.terrain),
        {
            "id": "river",
            "type": "line",
            "source": "geometry",
            "filter": ["==", ["get", "kind"], "river"],
            "paint": {
                "line-color": line.river,
                "line-width": [
                    "interpolate",
                    ["linear"],
                    ["zoom"],
                    7,
                    line.river_width_z7,
                    12,
                    line.river_width_z12,
                ],
            },
        },
        {
            "id": "road-casing",
            "type": "line",
            "source": "geometry",
            "filter": ["==", ["get", "kind"], "road"],
            "paint": {
                "line-color": line.road_casing,
                "line-width": [
                    "interpolate",
                    ["linear"],
                    ["zoom"],
                    9,
                    line.road_width_z9 + 1.5,
                    14,
                    line.road_width_z14 + 1.5,
                ],
            },
        },
        {
            "id": "road",
            "type": "line",
            "source": "geometry",
            "filter": ["==", ["get", "kind"], "road"],
            "paint": {
                "line-color": line.road,
                "line-width": [
                    "interpolate",
                    ["linear"],
                    ["zoom"],
                    9,
                    line.road_width_z9,
                    14,
                    line.road_width_z14,
                ],
            },
        },
        {
            "id": "transit",
            "type": "line",
            "source": "geometry",
            "filter": ["==", ["get", "layer"], "transit"],
            "paint": {
                # 线路配色以数据里的 line_color 为准（transit.geojson 白名单字段）；
                # 缺失时退回 palette 的 metro 色，避免整网变成同一种颜色。
                "line-color": ["coalesce", ["get", "line_color"], transit.metro],
                "line-width": 2.4,
            },
        },
        *_annotation_layers(config),
    ]
    return style


def _annotation_layers(config: AppConfig) -> list[dict[str, Any]]:
    """每个 kind 一层圆圈：`kinds.toml` 的 zoom 区间映射为 minzoom/maxzoom（D-018）。"""
    layers: list[dict[str, Any]] = []
    for name, kind in sorted(config.kinds.items()):
        layer: dict[str, Any] = {
            "id": f"annotation-{name}",
            "type": "circle",
            "source": "geometry",
            "filter": ["==", ["get", "kind"], name],
            "paint": {
                "circle-color": config.palette.label_tokens[kind.color_token].color,
                "circle-radius": ["match", ["get", "rank"], 1, 6, 2, 5, 3, 4, 4, 3, 2.5],
                "circle-stroke-color": config.palette.labels.halo,
                "circle-stroke-width": config.palette.labels.halo_width,
            },
        }
        if kind.default_min_zoom > 0:
            layer["minzoom"] = kind.default_min_zoom
        if kind.default_max_zoom < config.world.max_zoom:
            layer["maxzoom"] = kind.default_max_zoom
        layers.append(layer)
    return layers


def _background(color: str) -> dict[str, Any]:
    return {"id": "background", "type": "background", "paint": {"background-color": color}}


def _fill(layer_id: str, layer: str, color: str) -> dict[str, Any]:
    return {
        "id": f"{layer_id}-fill",
        "type": "fill",
        "source": "geometry",
        "filter": ["==", ["get", "layer"], layer],
        "paint": {"fill-color": color, "fill-opacity": 0.9},
    }


def _outline(layer_id: str, layer: str, color: str) -> dict[str, Any]:
    return {
        "id": f"{layer_id}-outline",
        "type": "line",
        "source": "geometry",
        "filter": ["==", ["get", "layer"], layer],
        "paint": {"line-color": color, "line-width": 1.2},
    }
