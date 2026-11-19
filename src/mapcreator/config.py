"""配置加载：`config/*.toml` → 类型化对象。

规则（docs/DATA_SPEC.md §1、§7、§8）：
- 带边界只有 `zoom_bands.toml` 一个来源（D-018）。
- kind 的 zoom 区间只用于生成 style filter，不反推带。
- 配置非法时必须报出**字段路径**，而不是笼统的 "invalid config"。
"""

from __future__ import annotations

import itertools
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from .errors import ConfigurationError, config_error_from
from .palette import PaletteConfig

LabelMode = Literal["point", "line", "none"]


class WorldSection(BaseModel):
    id: str
    name: str
    bounds: tuple[float, float, float, float] | None = None
    bounds_padding: float = Field(default=0.05, ge=0)
    default_zoom: float = 3.0
    min_zoom: float = 0.0
    max_zoom: float = 17.0
    planet_radius_km: float = 6371.0
    default_lang: str = "zh"
    languages: list[str] = Field(default_factory=lambda: ["zh"])

    @model_validator(mode="after")
    def _check_zoom(self) -> WorldSection:
        if self.min_zoom > self.max_zoom:
            raise ValueError("min_zoom 不能大于 max_zoom")
        if self.bounds is not None:
            west, south, east, north = self.bounds
            if not (west < east and south < north):
                raise ValueError(
                    "bounds 必须是 [west, south, east, north] 且 west<east、south<north"
                )
        return self


class WorldConfig(BaseModel):
    world: WorldSection


class KindDef(BaseModel):
    label_mode: LabelMode = "point"
    default_rank: int = Field(default=3, ge=1, le=5)
    default_min_zoom: float = 0.0
    default_max_zoom: float = 17.0
    icon: str | None = None
    color_token: str
    attrs_schema: str | None = None

    @model_validator(mode="after")
    def _check_zoom(self) -> KindDef:
        if self.default_min_zoom > self.default_max_zoom:
            raise ValueError("default_min_zoom 不能大于 default_max_zoom")
        return self


class KindsConfig(BaseModel):
    kinds: dict[str, KindDef]

    @field_validator("kinds")
    @classmethod
    def _non_empty(cls, value: dict[str, KindDef]) -> dict[str, KindDef]:
        if not value:
            raise ValueError("kinds 不能为空")
        return value


class BandDef(BaseModel):
    name: str
    min_zoom: int = Field(ge=0)
    max_zoom: int = Field(ge=0)
    simplify_tolerance: float = Field(ge=0)

    @model_validator(mode="after")
    def _check(self) -> BandDef:
        if self.min_zoom > self.max_zoom:
            raise ValueError("band 的 min_zoom 不能大于 max_zoom")
        return self


class BandsConfig(BaseModel):
    bands: list[BandDef]

    @model_validator(mode="after")
    def _contiguous(self) -> BandsConfig:
        ordered = sorted(self.bands, key=lambda b: b.min_zoom)
        names = [band.name for band in ordered]
        if len(names) != len(set(names)):
            raise ValueError(f"缩放带 name 必须唯一：{names}")
        for prev, cur in itertools.pairwise(ordered):
            if cur.min_zoom != prev.max_zoom + 1:
                raise ValueError(
                    f"缩放带必须连续：{prev.name} 结束于 {prev.max_zoom}，"
                    f"但 {cur.name} 从 {cur.min_zoom} 开始"
                )
        return self


class AppConfig(BaseModel):
    """进程内唯一配置对象；由 CLI/API 显式传入，不使用全局单例。"""

    root: Path
    world: WorldSection
    kinds: dict[str, KindDef]
    bands: list[BandDef]
    palette: PaletteConfig


def load_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigurationError(
            code="CONFIG_MISSING",
            message=f"配置文件不存在：{path.name}",
            path=path,
            remediation="确认仓库根目录下存在 config/ 且文件未被删除",
        )
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(
            code="CONFIG_INVALID_TOML",
            message=f"TOML 解析失败：{path.name}: {exc}",
            path=path,
            remediation="检查该行的引号/等号/数组括号",
        ) from exc


def _load_model[ModelT: BaseModel](model: type[ModelT], path: Path) -> ModelT:
    """TOML → Pydantic 模型；校验失败转成带字段路径的 ConfigurationError。"""
    try:
        return model.model_validate(load_toml(path))
    except ValidationError as exc:
        raise config_error_from(exc, path) from exc


def load_config(root: Path | None = None) -> AppConfig:
    """加载并交叉校验全部配置。root 为空时从源码位置向上找仓库根。"""
    base = root or find_repo_root()
    cfg_dir = base / "config"

    world = _load_model(WorldConfig, cfg_dir / "world.toml").world
    kinds_cfg = _load_model(KindsConfig, cfg_dir / "kinds.toml")
    bands_cfg = _load_model(BandsConfig, cfg_dir / "zoom_bands.toml")
    palette = _load_model(PaletteConfig, cfg_dir / "palette.toml")

    world_path = cfg_dir / "world.toml"
    kinds_path = cfg_dir / "kinds.toml"
    bands_path = cfg_dir / "zoom_bands.toml"

    if world.default_lang not in world.languages:
        raise ConfigurationError(
            code="CONFIG_INVALID",
            message=f"world.toml:world.default_lang: {world.default_lang!r} 不在 languages 中",
            path=world_path,
            remediation="把 default_lang 加入 languages，或改成已列出的语种",
        )
    if len(set(world.languages)) != len(world.languages):
        raise ConfigurationError(
            code="CONFIG_INVALID",
            message="world.toml:world.languages: 语种重复",
            path=world_path,
            remediation="删除重复项",
        )

    ordered_bands = sorted(bands_cfg.bands, key=lambda band: band.min_zoom)
    if ordered_bands[0].min_zoom != world.min_zoom:
        raise ConfigurationError(
            code="BAND_COVERAGE_GAP",
            message=(
                f"zoom_bands.toml: 第一个带从 {ordered_bands[0].min_zoom} 开始，"
                f"但 world.min_zoom 是 {world.min_zoom}"
            ),
            path=bands_path,
            remediation="让缩放带从 world.min_zoom 开始连续覆盖",
        )

    world_max = int(world.max_zoom)
    last_band = ordered_bands[-1]
    if last_band.max_zoom < world_max:
        raise ConfigurationError(
            code="BAND_COVERAGE_GAP",
            message=f"缩放带最大覆盖 {last_band.max_zoom}，小于 world.max_zoom {world_max}",
            path=bands_path,
            remediation="增加一个覆盖到 world.max_zoom 的带",
        )

    for name, kind in kinds_cfg.kinds.items():
        if kind.default_max_zoom > world.max_zoom:
            raise ConfigurationError(
                code="KIND_ZOOM_OUT_OF_RANGE",
                message=(
                    f"kinds.toml:kinds.{name}.default_max_zoom: "
                    f"{kind.default_max_zoom} 超出 world.max_zoom {world.max_zoom}"
                ),
                path=kinds_path,
                remediation="把该 kind 的默认上限降到 world.max_zoom 以内",
            )
        if kind.default_min_zoom < world.min_zoom:
            raise ConfigurationError(
                code="KIND_ZOOM_OUT_OF_RANGE",
                message=(
                    f"kinds.toml:kinds.{name}.default_min_zoom: "
                    f"{kind.default_min_zoom} 小于 world.min_zoom {world.min_zoom}"
                ),
                path=kinds_path,
                remediation="把该 kind 的默认下限提到 world.min_zoom 以上",
            )
        if kind.color_token not in palette.label_tokens:
            raise ConfigurationError(
                code="KIND_COLOR_TOKEN_UNKNOWN",
                message=(
                    f"kinds.toml:kinds.{name}.color_token: "
                    f"{kind.color_token!r} 未在 palette.toml 定义"
                ),
                path=kinds_path,
                remediation='在 palette.toml 增加对应 ["label.<name>"] 条目，或改用已有 token',
            )
        if kind.attrs_schema is not None and not (base / kind.attrs_schema).is_file():
            raise ConfigurationError(
                code="KIND_ATTRS_SCHEMA_MISSING",
                message=f"kinds.toml:kinds.{name}.attrs_schema: 找不到 {kind.attrs_schema}",
                path=kinds_path,
                remediation="补上 schemas/kinds/<kind>.schema.json，或改用已有 schema",
            )

    return AppConfig(
        root=base,
        world=world,
        kinds=kinds_cfg.kinds,
        bands=bands_cfg.bands,
        palette=palette,
    )


def find_repo_root(start: Path | None = None) -> Path:
    """从当前文件向上查找含 config/world.toml 的目录。"""
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "config" / "world.toml").is_file():
            return candidate
    raise ConfigurationError(
        code="REPO_ROOT_NOT_FOUND",
        message="找不到仓库根目录（未找到 config/world.toml）",
        path=here,
        remediation="在仓库内运行，或通过 root 参数显式指定",
    )
