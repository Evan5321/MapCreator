"""资产准备：图标栅格化、字体 glyph、调色板导出、哈希登记。

规则：少于约 100 个图标时前端运行时 addImage；超出再生成 sprite atlas。
     资产哈希写入 manifest，保证可重复构建可比对。
"""

from __future__ import annotations

from pathlib import Path

from ..config import AppConfig

TASK = "TASK-0006"


def prepare_icons(config: AppConfig, out_dir: Path) -> dict[str, str]:
    """返回 {icon_name: sha256}。"""
    raise NotImplementedError(TASK)


def prepare_glyphs(out_dir: Path) -> dict[str, str]:
    """拷贝/索引预生成 PBF；缺失即失败，不静默回退。"""
    raise NotImplementedError(TASK)


def verify_attribution(assets_dir: Path) -> list[str]:
    """每个资产必须在 ATTRIBUTION.md 中登记来源与许可证。"""
    raise NotImplementedError(TASK)
