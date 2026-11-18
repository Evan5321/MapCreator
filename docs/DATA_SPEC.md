# 数据规范（DATA_SPEC）

> 目标 ≤ 250 行。这是**唯一**的字段/格式事实来源；其他文档只链接，不复述。
> 相关：架构见 [`ARCHITECTURE.md`](ARCHITECTURE.md)，编辑器读写协议见 [`EDITOR.md`](EDITOR.md)。

## 1. 坐标与世界

- RFC 7946 GeoJSON：`[lon, lat]`，EPSG:4326 语义，但**是虚构地理**。
- 世界是**小范围有界区域**，按二维俯视处理；不处理纬度限制与投影变形（D-013）。
- 不跨越 ±180° 经线；不出现 ±90° 附近的点（不是约束，只是自然结果）。
- `bounds` 由构建从全部几何 + 标注的 bbox 推导，外扩 `world.toml#bounds_padding`（默认 0.05°），写入 `build/manifest.json`；`config/world.toml#bounds` 可覆盖。
- 缩放：`min_zoom = 0`，`max_zoom = 17`。
- 精度：**6 位小数**（约 0.1 m），构建前统一 `round(x, 6)` 并去掉 `-0.0`。

## 2. ID

| 类型 | 格式 | 正则 | 示例 |
|---|---|---|---|
| 几何 | `geo.<kind>.<slug>` | `^geo\.[a-z_]+(\.[a-z0-9_]+)+$` | `geo.river.silverrun` |
| 标注 | `anno.<kind>.<slug>` | `^anno\.[a-z_]+(\.[a-z0-9_]+)+$` | `anno.city.silverrun` |
| 关系 | `rel.<kind>.<slug>` | `^rel\.[a-z_]+(\.[a-z0-9_]+)+$` | `rel.metro_line.blue` |

- slug 只允许 `[a-z0-9_]`，小写；ID 全局唯一（几何与标注分别唯一，跨表也不重复）。
- ID 创建后**不改**；改名改 slug 会破坏外部引用与 URL，因此编辑器只允许改"名称"，不允许改 ID。
- 新增 ID 由服务端生成并做唯一性检查。

## 3. GeoJSON 规范

每个文件是一个 `FeatureCollection`：

```json
{
  "type": "Feature",
  "id": "geo.river.silverrun",
  "geometry": {"type": "LineString", "coordinates": [[-12.31, 4.52], [-11.88, 4.61]]},
  "properties": {"kind": "river", "width_class": 2}
}
```

规则：

1. `id` 必填且符合 §2；`kind` 必填且在 `config/kinds.toml` 注册。
2. `properties` **只允许**下表白名单键；`name`/`rank`/`min_zoom`/`description` 等标注语义**禁止**出现；`layer` **禁止**（图层由文件名 + `world/world.json` 决定）。
3. 多边形闭合、环方向正确、`shapely.is_valid` 为真；默认校验失败即中止，`--fix` 才 `make_valid` 并写警告。
4. 一个要素一行文本；由 `mapcreator format` 归一化（这就是 diff 友好性的来源）。
5. 单文件建议 ≤ 5 万行；超出按区域拆分并登记到 `world/world.json`。
6. **点不在这里**：点状标注只有 SQLite 坐标（D-015）。

| 文件 | 几何 | 允许 `kind` | 允许的其他属性 |
|---|---|---|---|
| `land.geojson` | Polygon/MultiPolygon | `continent` `island` | `land_class` ∈ {mainland, island} |
| `water.geojson` | Polygon/MultiPolygon | `ocean` `sea` `lake` | `water_class` ∈ {ocean, sea, lake} |
| `rivers.geojson` | LineString/MultiLineString | `river` `canal` | `width_class` ∈ 1–5 |
| `terrain.geojson` | Polygon/LineString | `mountain_range` `ridge` | `elev_class` ∈ 1–5 |
| `roads.geojson` | LineString/MultiLineString | `road` `street` `trail` | `road_class` ∈ 1–5, `surface` ∈ {paved, unpaved} |
| `transit.geojson` | LineString/MultiLineString | `metro` `bus` `rail` | `mode` ∈ {metro, bus, rail}, `line_color` `#RRGGBB` |
| `parks.geojson` | Polygon/MultiPolygon | `park` `reserve` `garden` | `protected` ∈ {true, false} |

## 4. SQLite schema

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
-- 必含：schema_version、default_lang、world_id

CREATE TABLE annotation (
  fid          INTEGER PRIMARY KEY,
  id           TEXT NOT NULL UNIQUE CHECK (id GLOB 'anno.*.*'),
  kind         TEXT NOT NULL,
  search_text  TEXT NOT NULL DEFAULT '',   -- 应用层维护：全部名称 + 描述
  parent_id    TEXT,
  geometry_id  TEXT,                       -- 点标注恒为 NULL
  lon          REAL NOT NULL,
  lat          REAL NOT NULL,
  label_mode   TEXT NOT NULL DEFAULT 'point' CHECK (label_mode IN ('point','line','none')),
  rank         INTEGER NOT NULL DEFAULT 3 CHECK (rank BETWEEN 1 AND 5),
  min_zoom     REAL,                       -- NULL = kind 默认
  max_zoom     REAL,
  icon         TEXT,
  description  TEXT,
  attrs        TEXT NOT NULL DEFAULT '{}',
  revision     INTEGER NOT NULL DEFAULT 1,
  updated_at   TEXT NOT NULL,              -- ISO 8601 UTC
  deleted_at   TEXT,
  CHECK (min_zoom IS NULL OR max_zoom IS NULL OR min_zoom <= max_zoom)
);

CREATE TABLE annotation_name (
  annotation_id TEXT NOT NULL REFERENCES annotation(id) ON DELETE CASCADE,
  lang          TEXT NOT NULL,             -- zh / zh-Hant / en / ja …
  name          TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'name' CHECK (role IN ('name','alias')),
  is_primary    INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0,1)),
  PRIMARY KEY (annotation_id, lang, name)
);
CREATE UNIQUE INDEX uq_annotation_name_primary ON annotation_name(annotation_id) WHERE is_primary = 1;

CREATE VIEW annotation_v AS
SELECT a.*, n.name AS name, n.lang AS name_lang
FROM annotation a LEFT JOIN annotation_name n
  ON n.annotation_id = a.id AND n.is_primary = 1;

CREATE INDEX idx_annotation_kind ON annotation(kind);
CREATE INDEX idx_annotation_parent ON annotation(parent_id);
CREATE INDEX idx_annotation_geometry ON annotation(geometry_id);
CREATE INDEX idx_annotation_live ON annotation(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_annotation_name_name ON annotation_name(name);

CREATE VIRTUAL TABLE annotation_rtree USING rtree(fid, min_lon, max_lon, min_lat, max_lat);
CREATE VIRTUAL TABLE annotation_fts USING fts5(
  search_text, content='annotation', content_rowid='fid', tokenize='trigram');

CREATE TABLE relation (id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL,
  attrs TEXT NOT NULL DEFAULT '{}');
CREATE TABLE relation_member (
  relation_id TEXT NOT NULL REFERENCES relation(id) ON DELETE CASCADE,
  member_id   TEXT NOT NULL,  -- stop/platform→annotation.id；section→geo.*
  role        TEXT NOT NULL,  -- stop / platform / section / child
  seq         INTEGER NOT NULL,
  PRIMARY KEY (relation_id, member_id, role));
```

FTS/RTree 由 `annotation` 上的 `AFTER INSERT/UPDATE/DELETE` 触发器维护；`search_text` **由应用层**在同一事务内重算（不用触发器，避免递归）。

## 5. 字段语义

| 字段 | 规则 |
|---|---|
| `kind` | 必须在 `config/kinds.toml`；决定默认 rank/zoom/icon/颜色 token |
| `label_mode` | `point` 点标注；`line` 沿线标注（必须关联线几何）；`none` 不画（仅数据） |
| `rank` | 1–5，越小越优先；决定字号、碰撞排序、图标优先级 |
| `min/max_zoom` | NULL → kind 默认值；显式值优先；构建期回填，**不写回库** |
| `geometry_id` | 仅线/面标注使用；点标注必须为 NULL；必须存在且类型匹配（line 需线几何） |
| `parent_id` | 地理/行政父级；必须存在，且**不得成环** |
| `attrs` | 业务属性 JSON；键受该 kind 的 `attrs_schema` 约束 |
| `revision` | 每次写入 +1（含名称/属性变更），用于乐观并发 |
| `deleted_at` | 软删除；所有查询过滤 `deleted_at IS NULL` |
| `annotation_name` | 一个标注可有任意语种名称与别名；**恰好一个** `is_primary=1` |
| `search_text` | 全部 `annotation_name.name` + `description`，空格连接 |

## 6. 搜索

- 查询长度 ≥ 3：`annotation_fts MATCH ?`（trigram 子串匹配）。
- 查询长度 1–2：回退 `LIKE '%q%'`（名称或 `search_text`）。2 万行内毫秒级。
- 排序：`rank ASC, name ASC`；默认 `LIMIT 20`。
- 语种过滤：`lang=` 可选，未给时对全部语种搜索，结果带命中的语种名。

## 7. 缩放带

`config/zoom_bands.toml` 是**唯一**的带边界来源（D-018）：

| 带 | 范围 | 典型内容 | 简化容差（度，初始值） |
|---|---|---|---|
| `z0-3` | 0–3 | 大陆、大洋、山脉 | 0.02 |
| `z4-6` | 4–6 | 国家/区域、主要城市 | 0.01 |
| `z7-9` | 7–9 | 城市、河流、主要道路 | 0.004 |
| `z10-12` | 10–12 | 区、公园、车站 | 0.001 |
| `z13-15` | 13–15 | 医院、学校、小 POI | 0.0002 |
| `z16-17` | 16–17 | 建筑级细节 | 0（不简化） |

- 简化用 `shapely.simplify(tol, preserve_topology=True)`。
- 标注进入其 `[min_zoom, max_zoom]` 覆盖到的每个带；带内仍用 style filter 精确判定。

## 8. kind 注册表（首批 27 个）

| 组 | kind（rank/min/max） |
|---|---|
| 自然 | `continent`(1/0/8) `ocean`(1/0/7) `sea`(2/3/9) `lake`(3/8/14) `island`(3/5/12) `mountain_range`(2/2/9) `peak`(3/6/15) `forest`(4/8/14) |
| 自然（线） | `river`(3/5/14) |
| 人文 | `country`(1/2/8) `region`(2/3/10) `city`(2/4/13) `town`(3/8/15) `village`(4/10/17) `district`(4/10/17) `park`(4/10/17) |
| 交通 | `metro_line`(3/9/15，线) `road`(4/9/15，线) `station`(4/11/17) `airport`(4/10/17) `port`(4/10/17) |
| 设施 | `hospital`(4/12/17) `school`(4/12/17) `university`(4/12/17) `museum`(5/13/17) `temple`(5/13/17) `market`(5/13/17) |

新增 kind 需要同时提供：`config/kinds.toml` 条目、`schemas/kinds/<kind>.schema.json`、图标（point 类）、调色板 token。

## 9. 校验规则

**错误（中止）**：解析失败、schema 失败、重复 ID、非法 ID、未注册 kind、`geometry_id`/`parent_id`/relation 成员不存在、`parent_id` 成环、点标注带 `geometry_id`、线标注关联非线几何、主名缺失或重复、几何无效、坐标越界、`min_zoom > max_zoom`、`rank` 越界、图标缺失、必填缺失。

**警告（继续）**：陆地/水域重叠、重复标注、某带标注超预算、几何无标注引用、多标注引用同一几何、只有中文名、负面积/极短线段/重复顶点。

强拓扑（共享边、河流连通）交给 QGIS Topology Checker，构建期不做。

## 10. dump / restore

- `annotations.sql` 只导**逻辑表**：`meta`、`annotation`、`annotation_name`、`relation`、`relation_member`，按外键顺序、主键稳定排序。
- 不导 FTS/RTree 及其影子表；`restore` 后自动 `rebuild` 并重填 RTree。
- `db verify-dump` 校验：行数、主键集合、`search_text` 与名称一致性。
- 构建前自动运行 `verify-dump`；不一致即失败并提示先 `db dump`。

## 11. 迁移与版本

- `meta.schema_version`（整数）随每次 DDL 变更 +1。
- 迁移脚本放 `src/mapcreator/db/migrations/NNNN_<desc>.sql`，必须幂等可重放。
- 破坏性迁移前必须 `mapcreator backup`，并在 `STATUS.md` 记录。
- 新增字段必须同时更新：本文件、`schemas/*.schema.json`、`docs/openapi.json`、golden 夹具。
