"""API 端点（契约见 docs/ARCHITECTURE.md §6）。

M0 只实现只读端点：`/api/health`、`/api/world`、`/api/data/{band}`、`/api/annotations/{id}`。
搜索/编辑端点分别在 TASK-0008 与编辑里程碑实现。
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .. import __version__
from ..build import manifest as manifest_mod
from ..config import AppConfig
from ..db import repo
from ..errors import MapCreatorError
from ..models import Annotation


def register_routes(
    app: FastAPI,
    *,
    config: AppConfig,
    build_dir: Path,
    db_path: Path,
    enable_edit: bool,
    enable_sql: bool,
) -> None:
    """注册只读端点；写端点未开启时保持 404。"""
    band_names = [band.name for band in config.bands]

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "version": __version__,
            "build_id": _build_id(build_dir),
            "edit": enable_edit,
            "sql": enable_sql,
        }

    @app.get("/api/world")
    def world() -> dict[str, Any]:
        manifest = _manifest(build_dir)
        return {
            "world": {
                "id": config.world.id,
                "name": config.world.name,
                "default_lang": config.world.default_lang,
                "languages": list(config.world.languages),
            },
            "bounds": manifest["bounds"],
            "bands": [
                {
                    "name": band.name,
                    "min_zoom": band.min_zoom,
                    "max_zoom": band.max_zoom,
                }
                for band in config.bands
            ],
            "kinds": {
                name: {
                    "label_mode": kind.label_mode,
                    "rank": kind.default_rank,
                    "min_zoom": kind.default_min_zoom,
                    "max_zoom": kind.default_max_zoom,
                    "icon": kind.icon,
                    "color": config.palette.label_tokens[kind.color_token].color,
                }
                for name, kind in sorted(config.kinds.items())
            },
            "typography": {
                str(rank): list(sizes)
                for rank, sizes in sorted(
                    {
                        1: config.palette.typography.rank1,
                        2: config.palette.typography.rank2,
                        3: config.palette.typography.rank3,
                        4: config.palette.typography.rank4,
                        5: config.palette.typography.rank5,
                    }.items()
                )
            },
            "build_id": manifest["build_version"],
        }

    @app.get("/api/data/{band}")
    def band_data(band: str) -> FileResponse:
        if band not in band_names:
            raise HTTPException(
                status_code=404,
                detail={"code": "BAND_UNKNOWN", "message": f"未知缩放带：{band}"},
            )
        path = build_dir / "data" / f"labels.{band}.geojson"
        if not path.is_file():
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "BAND_NOT_BUILT",
                    "message": f"分片未生成：{path.name}",
                    "remediation": "运行 `mapcreator build`",
                },
            )
        return FileResponse(path, media_type="application/geo+json")

    @app.get("/api/annotations/{annotation_id}")
    def annotation_detail(annotation_id: str) -> dict[str, Any]:
        """标注详情（全部名称 + attrs + 有效 zoom）。名称只从 SQLite 读（D-016）。"""
        annotation = _load_annotation(annotation_id)
        kind = config.kinds.get(annotation.kind)
        min_zoom = annotation.min_zoom
        max_zoom = annotation.max_zoom
        if kind is not None:
            if min_zoom is None:
                min_zoom = kind.default_min_zoom
            if max_zoom is None:
                max_zoom = kind.default_max_zoom
        primary = annotation.primary_name
        return {
            "id": annotation.id,
            "kind": annotation.kind,
            "lon": annotation.lon,
            "lat": annotation.lat,
            "rank": annotation.rank,
            "label_mode": annotation.label_mode,
            "min_zoom": min_zoom,
            "max_zoom": max_zoom,
            "icon": annotation.icon,
            "description": annotation.description,
            "attrs": annotation.attrs,
            "parent_id": annotation.parent_id,
            "geometry_id": annotation.geometry_id,
            "revision": annotation.revision,
            "names": [name.model_dump() for name in annotation.names],
            "primary_name": primary.name if primary is not None else None,
            "default_lang": config.world.default_lang,
            "color": config.palette.label_tokens[kind.color_token].color
            if kind is not None
            else None,
        }

    def _load_annotation(annotation_id: str) -> Annotation:
        if not db_path.is_file():
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "DB_MISSING",
                    "message": f"标注库不存在：{db_path}",
                    "path": str(db_path),
                    "remediation": "先运行 `uv run mapcreator annotations import` 建库",
                },
            )
        try:
            with closing(repo.connect(db_path)) as conn:
                annotation = repo.get_annotation(conn, annotation_id)
        except sqlite3.Error as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "DB_UNREADABLE",
                    "message": f"标注库读取失败：{exc}",
                    "path": str(db_path),
                    "remediation": "检查数据库是否损坏；必要时从 world/annotations.sql 重建",
                },
            ) from exc
        if annotation is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "ANNOTATION_NOT_FOUND",
                    "message": f"标注不存在或已删除：{annotation_id}",
                    "feature_id": annotation_id,
                    "remediation": "核对 ID 是否来自 /api/data/{band} 的 feature.id",
                },
            )
        return annotation


def _build_id(build_dir: Path) -> str | None:
    try:
        value = manifest_mod.read(build_dir / "manifest.json")["build_version"]
    except MapCreatorError:
        return None
    return value if isinstance(value, str) else None


def _manifest(build_dir: Path) -> dict[str, Any]:
    try:
        return manifest_mod.read(build_dir / "manifest.json")
    except MapCreatorError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": exc.code,
                "message": "构建产物缺失，无法提供地图数据",
                "remediation": "先运行 `uv run mapcreator build`",
            },
        ) from exc
