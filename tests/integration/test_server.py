"""集成：FastAPI 服务（/api/health、/api/world、/api/data/{band}、静态资源）。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from mapcreator.server.app import create_app

MANIFEST = {
    "schema_version": 1,
    "build_version": "0.1.0+test",
    "input_hash": "a" * 64,
    "bounds": [9.95, 6.95, 14.55, 11.05],
    "counts": {"geometry_total": 6, "annotation_total": 8},
    "world": {"id": "aetheria", "name": "Aetheria", "default_lang": "zh"},
    "files": [],
}


def _layout(tmp_path: Path) -> tuple[Path, Path]:
    build = tmp_path / "build"
    (build / "data").mkdir(parents=True)
    (build / "manifest.json").write_text(json.dumps(MANIFEST, ensure_ascii=False), encoding="utf-8")
    (build / "style.json").write_text('{"version": 8}', encoding="utf-8")
    (build / "data" / "labels.z0-3.geojson").write_text(
        '{"type": "FeatureCollection", "features": []}', encoding="utf-8"
    )
    web = tmp_path / "dist"
    web.mkdir()
    (web / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
    return build, web


def test_health_and_world(tmp_path: Path) -> None:
    build, web = _layout(tmp_path)
    client = TestClient(create_app(build_dir=build, web_dist=web))

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True
    assert health.json()["build_id"] == "0.1.0+test"

    world = client.get("/api/world")
    assert world.status_code == 200
    body = world.json()
    assert body["bounds"] == [9.95, 6.95, 14.55, 11.05]
    assert len(body["bands"]) == 6
    assert "city" in body["kinds"]
    assert body["typography"]["1"] == [18, 20]

    data = client.get("/api/data/z0-3")
    assert data.status_code == 200
    assert "FeatureCollection" in data.text

    assert client.get("/api/data/z99").status_code == 404
    assert client.get("/map/style.json").status_code == 200
    index = client.get("/")
    assert index.status_code == 200
    assert "ok" in index.text


def test_missing_manifest_returns_503(tmp_path: Path) -> None:
    build = tmp_path / "build"
    build.mkdir()
    web = tmp_path / "dist"
    web.mkdir()
    (web / "index.html").write_text("<html></html>", encoding="utf-8")

    client = TestClient(create_app(build_dir=build, web_dist=web))
    response = client.get("/api/world")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MANIFEST_MISSING"
    assert client.get("/api/health").json()["build_id"] is None
