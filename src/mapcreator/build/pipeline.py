"""构建编排（11 步，见 docs/ARCHITECTURE.md §5）。

关键约束：写入 `.tmp-build/` 成功后原子替换 `build/`；失败保留上一次产物；
         产物内不得出现时间戳。
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from .. import __version__
from ..config import AppConfig
from ..data.annotations import load_annotations
from ..data.geometry import normalize, round_coord, validate_geometry
from ..data.world import derive_bounds, load_features, load_world
from ..errors import DataValidationError
from ..models import Annotation, GeometryFeature, WorldDocument
from . import manifest as manifest_mod
from . import style as style_mod
from .bands import MAX_LABELS_PER_BAND, label_name, labels_for_band, resolved_zoom

TASK = "TASK-0005"
SCHEMA_VERSION = 1
TMP_DIR_NAME = ".tmp-build"
CONFIG_FILES = ("world.toml", "kinds.toml", "zoom_bands.toml", "palette.toml")


def run(
    config: AppConfig,
    *,
    data_root: Path | None = None,
    out_dir: Path | None = None,
    clean: bool = False,
) -> dict[str, Any]:
    """执行全量构建：`.tmp-build/` 写完 → 原子替换 `build/`，返回 manifest 摘要。"""
    root = data_root or config.root / "world"
    target = out_dir or config.root / "build"
    data = _collect(config, root)

    if clean:
        shutil.rmtree(target, ignore_errors=True)
    tmp = target.parent / TMP_DIR_NAME
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    try:
        digest = manifest_mod.input_hash(_input_paths(config, root), root=config.root)
        label_counts = _write_outputs(config, data, tmp)
        files = _file_entries(tmp)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "build_version": f"{__version__}+{digest[:12]}",
            "input_hash": digest,
            "world": {
                "id": data["document"].world.id,
                "name": data["document"].world.name,
                "default_lang": data["document"].world.default_lang,
            },
            "bounds": data["bounds"],
            "counts": {
                "geometry_total": len(data["features"]),
                "annotation_total": len(data["annotations"]),
                "by_layer": data["by_layer"],
                "labels_by_band": label_counts,
            },
            "bands": [
                {
                    "name": band.name,
                    "min_zoom": band.min_zoom,
                    "max_zoom": band.max_zoom,
                    "labels": label_counts[band.name],
                }
                for band in sorted(config.bands, key=lambda item: item.min_zoom)
            ],
            "files": files,
        }
        manifest_mod.write(manifest, tmp / "manifest.json")
        publish(tmp, target)
    except Exception:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        raise
    return {
        "build_dir": target.as_posix(),
        "manifest": manifest,
        "warnings": data["warnings"],
    }


def validate(config: AppConfig, *, data_root: Path | None = None) -> dict[str, Any]:
    """只校验、不写任何产物。"""
    data = _collect(config, data_root or config.root / "world")
    counts = {
        "geometry_total": len(data["features"]),
        "annotation_total": len(data["annotations"]),
        "by_layer": data["by_layer"],
        "annotation_kinds": dict(
            sorted(Counter(item.kind for item in data["annotations"]).items())
        ),
    }
    return {
        "world": {
            "id": data["document"].world.id,
            "name": data["document"].world.name,
        },
        "bounds": data["bounds"],
        "counts": counts,
        "bands": [
            {
                "name": band.name,
                "min_zoom": band.min_zoom,
                "max_zoom": band.max_zoom,
                "labels": len(labels_for_band(config, data["annotations"], band)),
            }
            for band in sorted(config.bands, key=lambda item: item.min_zoom)
        ],
        "warnings": data["warnings"],
    }


def run_incremental(config: AppConfig, changed: list[Path]) -> dict[str, Any]:
    """只重建受影响的图层/带（<= 3 s 预算）。"""
    raise NotImplementedError(TASK)


def publish(tmp_dir: Path, target: Path) -> None:
    """原子替换：失败不破坏旧产物。"""
    backup = target.with_name(f"{target.name}.old")
    if backup.exists():
        shutil.rmtree(backup)
    moved_old = False
    if target.exists():
        target.rename(backup)
        moved_old = True
    try:
        tmp_dir.rename(target)
    except OSError:
        if moved_old and backup.exists() and not target.exists():
            backup.rename(target)
        raise
    shutil.rmtree(backup, ignore_errors=True)


def _collect(config: AppConfig, data_root: Path) -> dict[str, Any]:
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
    features = [feature for items in layers.values() for feature in items]
    annotations = load_annotations(data_root)
    feature_ids = {feature.id for feature in features}

    problems: list[str] = []
    for annotation in annotations:
        if annotation.kind not in config.kinds:
            problems.append(f"{annotation.id}: kind {annotation.kind!r} 未在 kinds.toml 注册")
        if annotation.geometry_id is not None and annotation.geometry_id not in feature_ids:
            problems.append(f"{annotation.id}: geometry_id {annotation.geometry_id} 不存在")
        if annotation.label_mode != "none" and annotation.primary_name is None:
            problems.append(f"{annotation.id}: label_mode={annotation.label_mode} 但缺少主名")
    for feature in features:
        problems.extend(validate_geometry(feature))
    if problems:
        raise DataValidationError(
            code="BUILD_VALIDATION_FAILED",
            message=f"构建前校验失败（{len(problems)} 项）",
            path=data_root,
            remediation="按 details 修正数据后重试；几何问题可用 `validate --fix` 查看建议",
            details={"problems": problems},
        )

    bounds = derive_bounds(config, features, annotations)
    if bounds is None:
        raise DataValidationError(
            code="BOUNDS_UNDEFINED",
            message="没有几何或标注，无法推导 bounds",
            path=data_root,
            remediation="补数据，或在 config/world.toml 显式设置 bounds",
        )

    return {
        "document": document,
        "layers": layers,
        "features": features,
        "annotations": annotations,
        "bounds": bounds,
        "by_layer": {layer.id: len(layers[layer.id]) for layer in document.layers},
        "warnings": [],
    }


def _write_outputs(config: AppConfig, data: dict[str, Any], out: Path) -> dict[str, int]:
    document: WorldDocument = data["document"]
    layers: dict[str, list[GeometryFeature]] = data["layers"]
    annotations: list[Annotation] = data["annotations"]

    unified: list[dict[str, Any]] = []
    for layer in sorted(document.layers, key=lambda item: (item.order, item.id)):
        for feature in sorted(layers[layer.id], key=lambda item: item.id):
            normalized = normalize(feature)
            properties = dict(normalized.properties)
            properties["layer"] = layer.id
            unified.append(_feature(normalized.id, normalized.geometry, properties))
    for annotation in sorted(annotations, key=lambda item: item.id):
        unified.append(_annotation_feature(config, annotation))

    _write_json(out / "unified.geojson", {"type": "FeatureCollection", "features": unified})
    _write_json(out / "style.json", style_mod.generate(config))
    _write_json(
        out / "annotations.export.json",
        {
            "annotations": [
                _export_annotation(config, annotation)
                for annotation in sorted(annotations, key=lambda item: item.id)
            ]
        },
    )

    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for band in sorted(config.bands, key=lambda item: item.min_zoom):
        labels = labels_for_band(config, annotations, band)[:MAX_LABELS_PER_BAND]
        counts[band.name] = len(labels)
        features = [
            {
                "type": "Feature",
                "id": annotation.id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [round_coord(annotation.lon), round_coord(annotation.lat)],
                },
                "properties": _label_properties(config, annotation),
            }
            for annotation in labels
        ]
        _write_json(
            data_dir / f"labels.{band.name}.geojson",
            {"type": "FeatureCollection", "features": features},
        )
    return counts


def _feature(
    feature_id: str, geometry: dict[str, Any], properties: dict[str, Any]
) -> dict[str, Any]:
    return {"type": "Feature", "id": feature_id, "geometry": geometry, "properties": properties}


def _annotation_feature(config: AppConfig, annotation: Annotation) -> dict[str, Any]:
    properties = _label_properties(config, annotation)
    properties["label_mode"] = annotation.label_mode
    properties["geometry_id"] = annotation.geometry_id
    return _feature(
        annotation.id,
        {
            "type": "Point",
            "coordinates": [round_coord(annotation.lon), round_coord(annotation.lat)],
        },
        properties,
    )


def _label_properties(config: AppConfig, annotation: Annotation) -> dict[str, Any]:
    min_zoom, max_zoom = resolved_zoom(annotation, config.kinds[annotation.kind])
    return {
        "kind": annotation.kind,
        "rank": annotation.rank,
        "min_zoom": min_zoom,
        "max_zoom": max_zoom,
        "icon": annotation.icon,
        "name": label_name(annotation, config.world.default_lang),
    }


def _export_annotation(config: AppConfig, annotation: Annotation) -> dict[str, Any]:
    min_zoom, max_zoom = resolved_zoom(annotation, config.kinds[annotation.kind])
    return {
        "id": annotation.id,
        "kind": annotation.kind,
        "lon": round_coord(annotation.lon),
        "lat": round_coord(annotation.lat),
        "rank": annotation.rank,
        "label_mode": annotation.label_mode,
        "min_zoom": min_zoom,
        "max_zoom": max_zoom,
        "icon": annotation.icon,
        "description": annotation.description,
        "attrs": annotation.attrs,
        "parent_id": annotation.parent_id,
        "geometry_id": annotation.geometry_id,
        "names": [
            {"lang": name.lang, "name": name.name, "role": name.role, "is_primary": name.is_primary}
            for name in sorted(annotation.names, key=lambda item: (item.lang, item.role, item.name))
        ],
    }


def _input_paths(config: AppConfig, data_root: Path) -> list[Path]:
    paths = [config.root / "config" / name for name in CONFIG_FILES]
    paths.append(data_root / "world.json")
    document = load_world(data_root)
    paths.extend(data_root / layer.file for layer in document.layers)
    exported = data_root / "annotations.json"
    database = data_root / "annotations.db"
    if exported.is_file():
        paths.append(exported)
    elif database.is_file():
        paths.append(database)
    return [path for path in paths if path.is_file()]


def _file_entries(out: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(out.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        payload = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(out).as_posix(),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return entries


def _write_json(path: Path, payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")
