"""TASK-0005：构建管线、缩放带切分、manifest 与原子发布。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mapcreator.build import manifest as manifest_mod
from mapcreator.build import pipeline
from mapcreator.build.bands import bands_for, labels_for_band, resolved_zoom
from mapcreator.config import AppConfig, load_config
from mapcreator.errors import DataValidationError


@pytest.fixture(scope="module")
def config() -> AppConfig:
    return load_config()


def _tree_digest(root: Path) -> str:
    digests: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            digests.append(f"{path.relative_to(root).as_posix()}:{digest}")
    return hashlib.sha256("\n".join(digests).encode("utf-8")).hexdigest()


def test_input_hash_is_deterministic_and_content_sensitive(tmp_path: Path) -> None:
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("alpha", encoding="utf-8")
    second.write_text("beta", encoding="utf-8")

    baseline = manifest_mod.input_hash([first, second])
    assert baseline == manifest_mod.input_hash([second, first])
    second.write_text("beta2", encoding="utf-8")
    assert manifest_mod.input_hash([first, second]) != baseline


def test_manifest_roundtrip_and_missing_keys(tmp_path: Path) -> None:
    payload = {
        "schema_version": 1,
        "build_version": "0.1.0+abc",
        "input_hash": "d" * 64,
        "bounds": [0.0, 0.0, 1.0, 1.0],
        "counts": {"geometry_total": 0},
        "world": {"id": "aetheria"},
    }
    target = tmp_path / "manifest.json"
    manifest_mod.write(payload, target)
    assert manifest_mod.read(target) == payload
    assert target.read_text(encoding="utf-8").endswith("\n")

    manifest_mod.write({key: value for key, value in payload.items() if key != "bounds"}, target)
    with pytest.raises(DataValidationError) as excinfo:
        manifest_mod.read(target)
    assert excinfo.value.code == "MANIFEST_INCOMPLETE"


def test_bands_for_uses_only_configured_bands(config: AppConfig) -> None:
    ordered = sorted(config.bands, key=lambda band: band.min_zoom)
    assert bands_for(config, 0, 17) == ordered
    assert bands_for(config, 4, 4) == [
        band for band in ordered if band.min_zoom <= 4 <= band.max_zoom
    ]
    assert bands_for(config, 0, 0) == [ordered[0]]


def test_labels_for_band_backfills_kind_defaults(config: AppConfig, mini_world: Path) -> None:
    from mapcreator.data.annotations import load_annotations

    annotations = load_annotations(mini_world)
    city = next(item for item in annotations if item.id == "anno.city.silverrun")
    min_zoom, max_zoom = resolved_zoom(city, config.kinds[city.kind])
    assert (min_zoom, max_zoom) == (
        config.kinds[city.kind].default_min_zoom,
        config.kinds[city.kind].default_max_zoom,
    )

    mid_band = next(band for band in config.bands if band.min_zoom <= 6 <= band.max_zoom)
    labels = labels_for_band(config, annotations, mid_band)
    assert "anno.city.silverrun" in {item.id for item in labels}
    assert labels == sorted(labels, key=lambda item: (item.rank, item.id))


def test_build_writes_expected_artifacts(
    config: AppConfig, mini_world: Path, tmp_path: Path
) -> None:
    out = tmp_path / "build"
    result = pipeline.run(config, data_root=mini_world, out_dir=out)

    for name in ("unified.geojson", "annotations.export.json", "manifest.json"):
        assert (out / name).is_file(), name
    for band in config.bands:
        assert (out / "data" / f"labels.{band.name}.geojson").is_file()

    manifest = manifest_mod.read(out / "manifest.json")
    assert manifest["bounds"] == [9.95, 6.95, 14.55, 11.05]
    assert manifest["counts"]["geometry_total"] == 6
    assert manifest["counts"]["annotation_total"] == 8
    assert manifest["build_version"].startswith("0.1.0+")
    assert "timestamp" not in json.dumps(manifest)
    assert result["manifest"]["input_hash"] == manifest["input_hash"]
    assert not (tmp_path / pipeline.TMP_DIR_NAME).exists()

    unified = json.loads((out / "unified.geojson").read_text(encoding="utf-8"))
    features = unified["features"]
    by_layer: dict[str, list[str]] = {}
    for feature in features:
        layer = feature["properties"].get("layer")
        if layer is not None:
            by_layer.setdefault(layer, []).append(feature["id"])
    assert all(ids == sorted(ids) for ids in by_layer.values())
    annotation_positions = [
        index for index, feature in enumerate(features) if feature["id"].startswith("anno.")
    ]
    assert annotation_positions == sorted(annotation_positions)
    assert annotation_positions[-1] == len(features) - 1


def test_build_is_byte_identical_across_runs(
    config: AppConfig, mini_world: Path, tmp_path: Path
) -> None:
    out = tmp_path / "build"
    pipeline.run(config, data_root=mini_world, out_dir=out)
    first = _tree_digest(out)
    pipeline.run(config, data_root=mini_world, out_dir=out)
    assert _tree_digest(out) == first


def test_build_failure_keeps_previous_output(
    config: AppConfig, mini_world: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "build"
    pipeline.run(config, data_root=mini_world, out_dir=out)
    before = _tree_digest(out)

    def boom(*_args: object, **_kwargs: object) -> dict[str, int]:
        raise RuntimeError("模拟构建失败")

    monkeypatch.setattr(pipeline, "_write_outputs", boom)
    with pytest.raises(RuntimeError):
        pipeline.run(config, data_root=mini_world, out_dir=out)
    assert _tree_digest(out) == before


def test_validate_does_not_write(config: AppConfig, mini_world: Path, tmp_path: Path) -> None:
    payload = pipeline.validate(config, data_root=mini_world)
    assert payload["counts"]["geometry_total"] == 6
    assert payload["counts"]["annotation_total"] == 8
    assert not (tmp_path / "build").exists()
    assert not (mini_world / "build").exists()
