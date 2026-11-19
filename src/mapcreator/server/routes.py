"""API 端点（契约见 docs/ARCHITECTURE.md §6）。

M0 只实现只读端点：`/api/health`、`/api/world`、`/api/data/{band}`。
详情/搜索/编辑端点分别在 TASK-0007 与编辑里程碑实现。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .. import __version__
from ..build import manifest as manifest_mod
from ..config import AppConfig
from ..errors import MapCreatorError


def register_routes(
    app: FastAPI,
    *,
    config: AppConfig,
    build_dir: Path,
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
