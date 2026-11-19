"""TASK-0006：样式生成（确定性、调色板来源、无 glyph 依赖）。"""

from __future__ import annotations

import json

import pytest

from mapcreator.build.style import generate
from mapcreator.config import AppConfig, load_config


@pytest.fixture(scope="module")
def config() -> AppConfig:
    return load_config()


def test_style_uses_palette_and_generated_metadata(config: AppConfig) -> None:
    style = generate(config)
    assert style["version"] == 8
    assert style["sources"]["geometry"]["data"] == "unified.geojson"
    assert style["layers"][0]["id"] == "background"
    assert style["layers"][0]["paint"]["background-color"] == config.palette.surface.background
    assert style["metadata"]["mapcreator:kind"] == "generated"

    palette_colors = {
        config.palette.surface.land,
        config.palette.surface.water,
        config.palette.surface.park,
        config.palette.surface.terrain,
        config.palette.line.river,
        config.palette.line.road,
        config.palette.transit.metro,
        config.palette.transit.bus,
        config.palette.transit.rail,
        *(token.color for token in config.palette.label_tokens.values()),
    }
    dumped = json.dumps(style, ensure_ascii=False)
    for color in palette_colors:
        assert color in dumped, color


def test_style_has_no_glyph_dependent_layers(config: AppConfig) -> None:
    style = generate(config)
    assert "glyphs" not in style
    dumped = json.dumps(style)
    assert "text-field" not in dumped
    assert "icon-image" not in dumped


def test_style_is_deterministic(config: AppConfig) -> None:
    first = json.dumps(generate(config), ensure_ascii=False, sort_keys=True)
    second = json.dumps(generate(config), ensure_ascii=False, sort_keys=True)
    assert first == second


def test_kind_colors_cover_registered_kinds(config: AppConfig) -> None:
    style = generate(config)
    circle_layers = [layer for layer in style["layers"] if layer["type"] == "circle"]
    by_kind = {layer["id"].removeprefix("annotation-"): layer for layer in circle_layers}
    for name, kind in config.kinds.items():
        layer = by_kind[name]
        assert layer["filter"] == ["==", ["get", "kind"], name]
        assert layer["paint"]["circle-color"] == config.palette.label_tokens[kind.color_token].color
        if kind.default_min_zoom > 0:
            assert layer["minzoom"] == kind.default_min_zoom
        if kind.default_max_zoom < config.world.max_zoom:
            assert layer["maxzoom"] == kind.default_max_zoom
