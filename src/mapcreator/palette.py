"""调色板模型（config/palette.toml）。

契约（docs/DATA_SPEC.md §8）：颜色/字号/线宽**只**在 palette.toml 定义；
kind 的 `color_token` 必须指向本文件的 `["label.*"]` 条目。
"""

from __future__ import annotations

import re
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
TOKEN_RE = re.compile(r"^label\.[a-z_]+$")


def _check_hex(value: str) -> str:
    if not HEX_COLOR_RE.match(value):
        raise ValueError("颜色必须形如 #RRGGBB")
    return value


HexColor = Annotated[str, AfterValidator(_check_hex)]


class _StrictPalette(BaseModel):
    """调色板是显式契约：出现未知键说明写错了 token 名，必须报错而不是忽略。"""

    model_config = ConfigDict(extra="forbid")


class SurfacePalette(_StrictPalette):
    background: HexColor
    land: HexColor
    land_border: HexColor
    water: HexColor
    water_border: HexColor
    park: HexColor
    terrain: HexColor


class LinePalette(_StrictPalette):
    river: HexColor
    river_width_z7: float = Field(gt=0)
    river_width_z12: float = Field(gt=0)
    road_casing: HexColor
    road: HexColor
    road_width_z9: float = Field(gt=0)
    road_width_z14: float = Field(gt=0)
    rail_dash: HexColor


class TransitPalette(_StrictPalette):
    metro: HexColor
    bus: HexColor
    rail: HexColor


class LabelsPalette(_StrictPalette):
    halo: HexColor
    halo_width: float = Field(gt=0)


class PoiPalette(_StrictPalette):
    halo: HexColor
    size_z12: int = Field(gt=0)
    size_z15: int = Field(gt=0)


class TypographyPalette(_StrictPalette):
    font_family: str = Field(min_length=1)
    rank1: tuple[int, int]
    rank2: tuple[int, int]
    rank3: tuple[int, int]
    rank4: tuple[int, int]
    rank5: tuple[int, int]

    @field_validator("rank1", "rank2", "rank3", "rank4", "rank5")
    @classmethod
    def _positive_sizes(cls, value: tuple[int, int]) -> tuple[int, int]:
        if any(size <= 0 for size in value):
            raise ValueError("字号必须为正整数")
        if value[0] > value[1]:
            raise ValueError("字号必须按 [低缩放, 高缩放] 递增")
        return value


class LabelToken(_StrictPalette):
    color: HexColor


class PaletteConfig(_StrictPalette):
    surface: SurfacePalette
    line: LinePalette
    transit: TransitPalette
    labels: LabelsPalette
    poi: PoiPalette
    typography: TypographyPalette
    label_tokens: dict[str, LabelToken] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _lift_label_tokens(cls, data: Any) -> Any:
        """把 TOML 里的 `["label.nature"]` 顶层键收进 `label_tokens`。"""
        if not isinstance(data, dict):
            return data
        rest: dict[str, Any] = {}
        tokens: dict[str, Any] = {}
        for key, value in data.items():
            if key.startswith("label."):
                tokens[key] = value
            else:
                rest[key] = value
        if tokens:
            rest["label_tokens"] = tokens
        return rest

    @field_validator("label_tokens")
    @classmethod
    def _token_names(cls, value: dict[str, LabelToken]) -> dict[str, LabelToken]:
        if not value:
            raise ValueError("至少需要一个 label.* 语义颜色 token")
        for name in value:
            if not TOKEN_RE.match(name):
                raise ValueError(f"token 名 {name!r} 必须形如 label.<name>（小写字母/下划线）")
        return value
