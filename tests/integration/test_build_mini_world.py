"""集成：mini-world 全量构建。"""

from __future__ import annotations

from pathlib import Path

from mapcreator.build import manifest as manifest_mod
from mapcreator.build import pipeline
from mapcreator.config import load_config


def test_build_produces_manifest(mini_world: Path, tmp_path: Path) -> None:
    config = load_config()
    result = pipeline.run(config, data_root=mini_world, out_dir=tmp_path / "build")

    build_dir = Path(result["build_dir"])
    manifest = manifest_mod.read(build_dir / "manifest.json")
    assert manifest["world"]["id"] == "aetheria"
    assert manifest["input_hash"] == result["manifest"]["input_hash"]
    assert manifest["counts"]["labels_by_band"]
    assert all(item["bytes"] > 0 for item in manifest["files"])
