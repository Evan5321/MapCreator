"""从 Pydantic 模型导出 JSON Schema。

生成物（**禁止手改**，改模型后重跑 `mapcreator schema`）：
- schemas/world.schema.json              world/world.json
- schemas/config/world.schema.json       config/world.toml
- schemas/config/kinds.schema.json       config/kinds.toml
- schemas/config/zoom-bands.schema.json  config/zoom_bands.toml
- schemas/config/palette.schema.json     config/palette.toml
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from .config import BandsConfig, KindsConfig, WorldConfig
from .models import WorldDocument
from .palette import PaletteConfig

SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "world.schema.json": WorldDocument,
    "config/world.schema.json": WorldConfig,
    "config/kinds.schema.json": KindsConfig,
    "config/zoom-bands.schema.json": BandsConfig,
    "config/palette.schema.json": PaletteConfig,
}


def export_schemas(out_dir: Path) -> list[Path]:
    """按固定顺序写出全部 schema；返回写出的文件路径。"""
    written: list[Path] = []
    for relative, model in SCHEMA_MODELS.items():
        path = out_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(
            model.model_json_schema(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        path.write_text(text + "\n", encoding="utf-8", newline="\n")
        written.append(path)
    return written
