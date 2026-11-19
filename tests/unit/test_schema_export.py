"""JSON Schema 导出必须确定，且仓库内生成物与模型同步（TASK-0003）。"""

from __future__ import annotations

import json
from pathlib import Path

from mapcreator.schema_export import SCHEMA_MODELS, export_schemas


def _snapshot(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in sorted(directory.rglob("*.json"))
    }


def test_export_is_deterministic(tmp_path: Path) -> None:
    export_schemas(tmp_path / "a")
    export_schemas(tmp_path / "b")

    first = _snapshot(tmp_path / "a")
    second = _snapshot(tmp_path / "b")

    assert first == second
    assert set(first) == set(SCHEMA_MODELS)


def test_committed_schemas_are_up_to_date(repo_root: Path, tmp_path: Path) -> None:
    export_schemas(tmp_path)
    generated = _snapshot(tmp_path)
    for relative in SCHEMA_MODELS:
        committed = repo_root / "schemas" / relative
        assert committed.is_file(), f"缺少生成物 {relative}（运行 mapcreator schema）"
        assert committed.read_bytes() == generated[relative], f"{relative} 与模型不一致"


def test_world_document_schema_describes_manifest(tmp_path: Path) -> None:
    export_schemas(tmp_path)
    payload = json.loads((tmp_path / "world.schema.json").read_text(encoding="utf-8"))

    assert payload["title"] == "WorldDocument"
    assert set(payload["required"]) == {"schema_version", "world", "layers"}
    assert "layer" in json.dumps(payload["properties"]["layers"], ensure_ascii=False).lower()
