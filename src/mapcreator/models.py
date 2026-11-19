"""领域模型：几何要素、标注、多语言名称。

刻意**暂时不**导入 `geojson_pydantic`：骨架阶段不猜第三方库 API，TASK-0003 再切换。
这里只定义本项目自己的契约与校验，字段与 docs/DATA_SPEC.md 一一对应。
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GEO_ID_RE = re.compile(r"^geo\.[a-z_]+(\.[a-z0-9_]+)+$")
ANNO_ID_RE = re.compile(r"^anno\.[a-z_]+(\.[a-z0-9_]+)+$")
REL_ID_RE = re.compile(r"^rel\.[a-z_]+(\.[a-z0-9_]+)+$")
LANG_RE = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$")

LabelMode = Literal["point", "line", "none"]
GeometryType = Literal["Point", "LineString", "MultiLineString", "Polygon", "MultiPolygon"]


class AnnotationName(BaseModel):
    lang: str
    name: str = Field(min_length=1, max_length=200)
    role: Literal["name", "alias"] = "name"
    is_primary: bool = False

    @field_validator("lang")
    @classmethod
    def _lang(cls, value: str) -> str:
        if not LANG_RE.match(value):
            raise ValueError("lang 必须是 BCP 47（如 zh / zh-Hant / en）")
        return value


class Annotation(BaseModel):
    """标注：坐标自带（点标注不建几何），名称在 names，业务属性在 attrs。"""

    id: str
    kind: str
    parent_id: str | None = None
    geometry_id: str | None = None
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    label_mode: LabelMode = "point"
    rank: int = Field(default=3, ge=1, le=5)
    min_zoom: float | None = None
    max_zoom: float | None = None
    icon: str | None = None
    description: str | None = None
    attrs: dict[str, Any] = Field(default_factory=dict)
    revision: int = Field(default=1, ge=1)
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    names: list[AnnotationName] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _id(cls, value: str) -> str:
        if not ANNO_ID_RE.match(value):
            raise ValueError("标注 ID 必须形如 anno.<kind>.<slug>（只含小写字母/数字/下划线）")
        return value

    @field_validator("geometry_id")
    @classmethod
    def _geometry_id(cls, value: str | None) -> str | None:
        if value is not None and not GEO_ID_RE.match(value):
            raise ValueError("geometry_id 必须形如 geo.<kind>.<slug>")
        return value

    @model_validator(mode="after")
    def _rules(self) -> Annotation:
        if (
            self.min_zoom is not None
            and self.max_zoom is not None
            and self.min_zoom > self.max_zoom
        ):
            raise ValueError("min_zoom 不能大于 max_zoom")
        if self.geometry_id is not None and self.label_mode == "point":
            raise ValueError("点标注不能关联几何（D-015）；线/面标注请用 label_mode=line 或 none")
        if self.names:
            primaries = [n for n in self.names if n.is_primary]
            if len(primaries) != 1:
                raise ValueError(f"必须恰好一个主名，当前 {len(primaries)} 个")
        return self

    @property
    def primary_name(self) -> AnnotationName | None:
        return next((n for n in self.names if n.is_primary), None)


class GeometryFeature(BaseModel):
    """GeoJSON Feature 的最小投影。properties 只允许几何属性（不允许 name/rank/layer）。"""

    type: Literal["Feature"] = "Feature"
    id: str
    geometry: dict[str, Any]
    properties: dict[str, Any]

    @field_validator("id")
    @classmethod
    def _id(cls, value: str) -> str:
        if not GEO_ID_RE.match(value):
            raise ValueError("几何 ID 必须形如 geo.<kind>.<slug>")
        return value

    @model_validator(mode="after")
    def _properties(self) -> GeometryFeature:
        if "kind" not in self.properties:
            raise ValueError("properties.kind 必填")
        forbidden = {"name", "rank", "min_zoom", "max_zoom", "description", "layer"}
        hit = forbidden & set(self.properties)
        if hit:
            raise ValueError(f"properties 不允许出现标注语义字段：{sorted(hit)}")
        return self

    @property
    def geometry_type(self) -> str:
        return str(self.geometry.get("type", ""))


class WorldMeta(BaseModel):
    """world/world.json 的 `world` 段。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1)
    default_lang: str


class LayerDef(BaseModel):
    """world/world.json 的图层清单条目；file 必须是 world 目录内的相对路径。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    file: str = Field(min_length=1)
    geometry: list[GeometryType] = Field(min_length=1)
    order: int

    @field_validator("file")
    @classmethod
    def _relative_file(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if normalized.startswith("/") or ".." in normalized.split("/"):
            raise ValueError("file 必须是 world 目录内的相对路径（不得使用绝对路径或 ..）")
        return normalized


class WorldCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    features: int = Field(default=0, ge=0)
    annotations: int = Field(default=0, ge=0)


class WorldDocument(BaseModel):
    """world/world.json：世界元数据、图层清单、schema 版本。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_uri: str | None = Field(default=None, alias="$schema")
    schema_version: int = Field(ge=1)
    world: WorldMeta
    layers: list[LayerDef] = Field(min_length=1)
    counts: WorldCounts = Field(default_factory=WorldCounts)

    @model_validator(mode="after")
    def _unique_layers(self) -> WorldDocument:
        ids = [layer.id for layer in self.layers]
        if len(ids) != len(set(ids)):
            raise ValueError(f"layer.id 必须唯一：{ids}")
        files = [layer.file for layer in self.layers]
        if len(files) != len(set(files)):
            raise ValueError(f"layer.file 必须唯一：{files}")
        return self
