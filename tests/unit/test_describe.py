"""`describe --json` 与 mini-world 一致性（TASK-0003）。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from mapcreator.cli import app

runner = CliRunner()


def _describe(root: Path) -> tuple[int, dict[str, object]]:
    result = runner.invoke(app, ["describe", "--json", "--root", str(root)])
    return result.exit_code, json.loads(result.stdout)


def test_mini_world_counts_and_bounds(mini_world: Path) -> None:
    exit_code, payload = _describe(mini_world)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["warnings"] == []

    counts = payload["counts"]
    assert counts["geometry_total"] == 6
    assert counts["annotation_total"] == 8
    assert counts["by_layer"] == {
        "land": 1,
        "water": 1,
        "parks": 0,
        "terrain": 1,
        "rivers": 2,
        "roads": 0,
        "transit": 1,
    }
    assert counts["geometry_kinds"] == {
        "continent": 1,
        "metro": 1,
        "mountain_range": 1,
        "river": 2,
        "sea": 1,
    }
    assert counts["annotation_kinds"] == {
        "city": 2,
        "hospital": 1,
        "market": 1,
        "metro_line": 1,
        "museum": 1,
        "school": 1,
        "temple": 1,
    }

    # 外扩 0.05 后的 bounds；与 world.toml 的 bounds_padding 一致
    assert payload["bounds"] == [9.95, 6.95, 14.55, 11.05]
    assert len(payload["kinds"]) == 27
    assert [band["name"] for band in payload["bands"]] == [
        "z0-3",
        "z4-6",
        "z7-9",
        "z10-12",
        "z13-15",
        "z16-17",
    ]


def test_unregistered_geometry_kind_fails(mini_world: Path, tmp_path: Path) -> None:
    root = tmp_path / "world"
    shutil.copytree(mini_world, root)
    land = root / "geometry" / "land.geojson"
    land.write_text(
        land.read_text(encoding="utf-8").replace('"kind": "continent"', '"kind": "landmass"'),
        encoding="utf-8",
        newline="\n",
    )

    exit_code, payload = _describe(root)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["errors"][0]["code"] == "KIND_NOT_ALLOWED"


def test_missing_geometry_file_fails(mini_world: Path, tmp_path: Path) -> None:
    root = tmp_path / "world"
    shutil.copytree(mini_world, root)
    (root / "geometry" / "water.geojson").unlink()

    exit_code, payload = _describe(root)

    assert exit_code == 1
    assert payload["errors"][0]["code"] == "GEOMETRY_MISSING"
    assert payload["errors"][0]["path"].endswith("water.geojson")


def test_annotation_with_geometry_on_point_is_rejected(mini_world: Path, tmp_path: Path) -> None:
    root = tmp_path / "world"
    shutil.copytree(mini_world, root)
    path = root / "annotations.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["annotations"][0]["geometry_id"] = "geo.metro.blue"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8", newline="\n")

    exit_code, result = _describe(root)

    assert exit_code == 1
    assert result["errors"][0]["code"] == "SCHEMA_INVALID"
    assert result["errors"][0]["feature_id"] == "anno.city.silverrun"
