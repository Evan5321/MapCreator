"""配置加载与字段路径报错（TASK-0003）。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from mapcreator.config import load_config
from mapcreator.errors import ConfigurationError

# docs/DATA_SPEC.md §8：首批 27 个 kind 的 (rank, min_zoom, max_zoom)
DATA_SPEC_KINDS: dict[str, tuple[int, float, float]] = {
    "continent": (1, 0, 8),
    "ocean": (1, 0, 7),
    "sea": (2, 3, 9),
    "lake": (3, 8, 14),
    "island": (3, 5, 12),
    "mountain_range": (2, 2, 9),
    "peak": (3, 6, 15),
    "forest": (4, 8, 14),
    "river": (3, 5, 14),
    "country": (1, 2, 8),
    "region": (2, 3, 10),
    "city": (2, 4, 13),
    "town": (3, 8, 15),
    "village": (4, 10, 17),
    "district": (4, 10, 17),
    "park": (4, 10, 17),
    "metro_line": (3, 9, 15),
    "road": (4, 9, 15),
    "station": (4, 11, 17),
    "airport": (4, 10, 17),
    "port": (4, 10, 17),
    "hospital": (4, 12, 17),
    "school": (4, 12, 17),
    "university": (4, 12, 17),
    "museum": (5, 13, 17),
    "temple": (5, 13, 17),
    "market": (5, 13, 17),
}


def _copy_repo_config(repo_root: Path, target: Path) -> Path:
    shutil.copytree(repo_root / "config", target / "config")
    shutil.copytree(repo_root / "schemas", target / "schemas")
    return target


def test_loads_four_toml_and_matches_data_spec(repo_root: Path) -> None:
    config = load_config(repo_root)

    assert set(config.kinds) == set(DATA_SPEC_KINDS)
    for name, (rank, min_zoom, max_zoom) in DATA_SPEC_KINDS.items():
        kind = config.kinds[name]
        assert (kind.default_rank, kind.default_min_zoom, kind.default_max_zoom) == (
            rank,
            min_zoom,
            max_zoom,
        ), name

    assert [(band.name, band.min_zoom, band.max_zoom) for band in config.bands] == [
        ("z0-3", 0, 3),
        ("z4-6", 4, 6),
        ("z7-9", 7, 9),
        ("z10-12", 10, 12),
        ("z13-15", 13, 15),
        ("z16-17", 16, 17),
    ]
    assert config.palette.surface.land == "#2f3b2a"
    assert set(config.palette.label_tokens) == {
        "label.nature",
        "label.water",
        "label.political",
        "label.transit",
        "label.facility",
    }


def test_invalid_kind_value_reports_field_path(repo_root: Path, tmp_path: Path) -> None:
    root = _copy_repo_config(repo_root, tmp_path)
    path = root / "config" / "kinds.toml"
    text = path.read_text(encoding="utf-8").replace(
        '[kinds.city]\nlabel_mode = "point"\ndefault_rank = 2',
        '[kinds.city]\nlabel_mode = "point"\ndefault_rank = 9',
    )
    path.write_text(text, encoding="utf-8", newline="\n")

    with pytest.raises(ConfigurationError) as excinfo:
        load_config(root)

    assert excinfo.value.code == "CONFIG_INVALID"
    assert "kinds.toml:kinds.city.default_rank" in excinfo.value.message


def test_invalid_palette_color_reports_field_path(repo_root: Path, tmp_path: Path) -> None:
    root = _copy_repo_config(repo_root, tmp_path)
    path = root / "config" / "palette.toml"
    text = path.read_text(encoding="utf-8").replace('land = "#2f3b2a"', 'land = "dark-green"')
    path.write_text(text, encoding="utf-8", newline="\n")

    with pytest.raises(ConfigurationError) as excinfo:
        load_config(root)

    assert excinfo.value.code == "CONFIG_INVALID"
    assert "palette.toml:surface.land" in excinfo.value.message


def test_unknown_color_token_is_rejected(repo_root: Path, tmp_path: Path) -> None:
    root = _copy_repo_config(repo_root, tmp_path)
    path = root / "config" / "kinds.toml"
    text = path.read_text(encoding="utf-8").replace(
        'color_token = "label.political"', 'color_token = "label.missing"'
    )
    path.write_text(text, encoding="utf-8", newline="\n")

    with pytest.raises(ConfigurationError) as excinfo:
        load_config(root)

    assert excinfo.value.code == "KIND_COLOR_TOKEN_UNKNOWN"
    assert "label.missing" in excinfo.value.message


def test_missing_config_reports_path(repo_root: Path, tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError) as excinfo:
        load_config(tmp_path)

    assert excinfo.value.code == "CONFIG_MISSING"
    assert excinfo.value.remediation
    assert excinfo.value.path is not None
