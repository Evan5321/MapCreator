# MapCreator 开发准备文档

> **版本**：0.2（第 18 节决策已确认；可进入 TASK-0001）  
> **日期**：2026-11-03  
> **状态**：技术方向已确认（2026-11-03 复核 §18）；确认后拆分为 `AGENTS.md` 与 `docs/*.md`  
> **复核记录**：2026-11-03 与人类逐条确认 §18 十问；结论写入 §18 与 §19（D-013–D-021）
> **仓库**：`D:\Git_Projects\MapCreator`  
> **开发模式**：AI Agent 主导实现，人类负责决策、验收与方向调整

---

## 目录

1. [文档定位与阅读方式](#1-文档定位与阅读方式)
2. [项目定位与边界](#2-项目定位与边界)
3. [总体架构](#3-总体架构)
4. [技术栈与开源复用](#4-技术栈与开源复用)
5. [数据规范](#5-数据规范)
6. [构建管线](#6-构建管线)
7. [渲染与缩放分级标注](#7-渲染与缩放分级标注)
8. [编辑器](#8-编辑器)
9. [本地应用与运行](#9-本地应用与运行)
10. [AI Agent 开发协议](#10-ai-agent-开发协议)
11. [仓库结构](#11-仓库结构)
12. [里程碑与首批任务](#12-里程碑与首批任务)
13. [测试与质量门禁](#13-测试与质量门禁)
14. [性能预算](#14-性能预算)
15. [风险与对策](#15-风险与对策)
16. [许可证与合规](#16-许可证与合规)
17. [端到端应用流程](#17-端到端应用流程)
18. [待确认问题与复核结论](#18-待确认问题与复核结论)
19. [决策记录（ADR 摘要）](#19-决策记录adr-摘要)
20. [术语表](#20-术语表)

---

## 1. 文档定位与阅读方式

本文档是项目的**开发契约**，不是灵感记录。开发启动后，稳定内容会拆分为：

- `AGENTS.md`：AI Agent 的唯一入口（命令、规则、阅读顺序、DoD）；
- `docs/ARCHITECTURE.md`：架构与数据流；
- `docs/DATA_SPEC.md`：坐标、GeoJSON、SQLite 表结构与校验规则；
- `docs/EDITOR.md`：Web 编辑器与 QGIS 工作流；
- `docs/TESTING.md`：测试与验收；
- `docs/DECISIONS.md`：ADR 决策记录；
- `docs/STATUS.md`：当前进度、已知问题、下一步；
- `docs/DEPENDENCIES.md`：依赖、版本、许可证、Windows 支持情况。

标记约定：

- **【已定】**：默认决策。除非人类明确修改，AI 不得擅自变更。
- **【待确认】**：需要人类拍板，AI 不应自行假设。
- **【建议】**：推荐做法。实现中可调整，但必须写入 ADR。
- **【禁止】**：不得采用的做法。

AI 阅读顺序：第 2、3、4、10 节 → 当前任务相关章节 → 任务文件。人类评审重点：第 18、19、15 节。

---

## 2. 项目定位与边界

### 2.1 一句话描述

一个**本地优先、Python 主导、可缩放分级标注**的架空世界地图浏览与编辑工具；地图几何用 AI 可读的 JSON/GeoJSON 描述，标注与搜索用 SQLite 管理；尽量复用成熟开源项目，不重复造地图引擎。

### 2.2 核心目标

1. 像电子地图一样缩放、平移；按缩放级别显示不同层级的标注。
2. 地图几何（陆地、海洋、河流、山脉、道路、轨道、公园边界等）由 GeoJSON 描述，AI 可读、可校验、可 diff。
3. 标注（名称、等级、缩放范围、图标、描述、属性）用 SQLite 管理，支持 SQL 查询、全文搜索、空间索引。
4. 配套 Web 编辑器，覆盖点、线、面绘制与属性编辑；大批量/拓扑编辑可交给 QGIS。
5. 所有开发、构建、验证、截图、查询都可以由 AI Agent 通过命令行完成。
6. 目标地图规模：约 **≤ 5 万几何要素 + ≤ 2 万标注**；超出后先做性能优化，不提前引入复杂瓦片管线。

### 2.3 MVP 范围

- 缩放/平移、世界边界限制、URL 状态（缩放/中心/选中要素）。
- 基础几何图层：陆地、海洋、河流、山脉、道路、轨道交通、公园。
- 点/线标注分级显示、碰撞避让、图标与文字样式。
- 搜索（中文/英文/别名）、点选详情、结果定位与高亮。
- Web 编辑器：点/线/面创建与编辑、属性表单、保存校验、撤销/重做、软删除。
- 一条命令完成校验、构建、启动、截图与检查。

### 2.4 非目标（当前阶段）

- 真实地理精度、导航、路径规划、公交 ETA。
- 多人在线协作、账号体系、权限系统。
- 移动原生 App、3D 地球、VR。
- 从零实现地图渲染引擎、瓦片服务器、绘图库。
- 浏览器内完整 GIS 拓扑编辑（交给 QGIS）。
- 对任意字体做完整字形生成（采用固定字体 + 本地 CJK 字体方案）。

### 2.5 关键约束

- **【已定】** 本地优先，默认绑定 `127.0.0.1`。
- **【已定】** Python 为主语言；JavaScript 只做浏览器壳与交互。
- **【已定】** 优先复用开源项目；自研组件必须有 ADR 说明。
- **【已定】** 所有开发环节必须 AI 可读、可执行、可验证。
- **【已定】** 小地图优先：先用简单方案跑通，性能不足再优化。
- **【已定】** 数据写入必须经过统一校验路径，不允许前端直接改文件/数据库。
- **【已定】** 构建产物必须可重复生成，并带 manifest。
- **【已定】** 世界是**小范围、有界、二维俯视**的地图区域；不处理纬度限制与投影变形，也不做虚构星球的比例尺校准（D-013）。
- **【已定】** 名称、别名、描述、属性只存在于 SQLite；GeoJSON 与前端 JSON 不重复存名称（D-016）。
- **【已定】** 点状标注不生成 GeoJSON 几何，坐标直接存在 `annotation.lon/lat`（D-015）。
- **【已定】** 跨模块与 API 传递以 **ID** 为准；详情按 ID 回查数据库，不做宽表广播（D-016）。

---

## 3. 总体架构

### 3.1 分层图

```text
┌──────────────────────────────────────────────────────┐
│ Web Client（JavaScript）                              │
│ MapLibre GL JS  +  Terra Draw  +  轻量 UI             │
└───────────────────────────┬──────────────────────────┘
                            │ HTTP / JSON / GeoJSON
┌───────────────────────────▼──────────────────────────┐
│ FastAPI（本地服务，单进程）                            │
│ 静态资源 / 数据 API / 编辑 API / 只读 SQL 查询         │
└───────────────────────────┬──────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────┐
│ Python Build Pipeline                                 │
│ 校验 → 合并 → 样式生成 → 分级分片 → manifest          │
└───────────┬───────────────────────────────┬──────────┘
            │                               │
┌───────────▼─────────────┐     ┌───────────▼──────────┐
│ 真源（Source of Truth）  │     │ 可选外部编辑器         │
│ world/geometry/*.geojson│     │ QGIS（批量/拓扑）      │
│ world/annotations.db    │     │ 通过导出/导入往返      │
└─────────────────────────┘     └──────────────────────┘
```

### 3.2 职责划分

| 层 | 职责 | 不负责 |
|---|---|---|
| Web Client | 显示地图、交互、绘制、表单 | 数据校验、持久化、切片 |
| FastAPI | 静态文件、查询 API、编辑 API、只读 SQL | 复杂渲染、批量 GIS 运算 |
| Build Pipeline | 数据校验、合并、样式、分级分片、manifest | 用户交互 |
| GeoJSON | 几何真源 | 名称/等级/描述等标注元数据 |
| SQLite | 标注、**多语言名称**、关系、搜索、空间索引真源 | 复杂多边形几何 |
| QGIS | 批量绘制、拓扑检查、属性批量编辑 | 应用运行时 |

### 3.3 数据流

**浏览**：源数据 → `mapcreator build` → `build/` → FastAPI 提供静态数据/API → MapLibre 渲染。

**编辑**：Web 编辑器或 QGIS → 统一导入 API/CLI → Pydantic + Shapely 校验 → 写入真源 → 增量构建 → 刷新页面。

**AI 查询**：`mapcreator describe/query/export` → JSON 输出；AI 不直接解析二进制数据库。

### 3.4 关键原则

1. **复用优先**：引擎、绘制、表单、校验、测试全部优先用开源项目。
2. **职责单一**：几何在 GeoJSON，标注在 SQLite；同一字段只存一处。
3. **单一写路径**：所有写入经过 Python 校验层；禁止浏览器直接写文件或 SQL。
4. **构建可重复**：稳定排序、固定精度、无构建时间戳、原子发布。
5. **显式优于隐式**：配置在 `config/*.toml`，规则可读、可测试。
6. **ID 是契约**：几何与标注通过稳定 ID 关联；构建时强校验。
7. **可验证完成**：每个任务必须有命令、测试或截图证据。

---

## 4. 技术栈与开源复用

### 4.1 核心选型

| 领域 | 选型 | 角色 | 备注 |
|---|---|---|---|
| 语言 | Python 3.12+ | 主语言 | 后端、构建、CLI、测试 |
| 包管理 | `uv` | 环境/锁文件 | `uv.lock` 必须提交 |
| CLI | Typer | 单一入口 | 自动 help、类型提示 |
| Web API | FastAPI + Uvicorn | 本地服务 | 自动 OpenAPI |
| 配置/校验 | Pydantic v2 + pydantic-settings | 类型化配置/数据校验 | 生成 JSON Schema |
| GeoJSON 模型 | `geojson-pydantic` | 标准 GeoJSON 解析/校验 | 避免手写模型 |
| 几何处理 | Shapely | 有效性、简化、锚点、空间运算 | 核心几何库 |
| 数据库 | SQLite（stdlib `sqlite3`） | 标注/关系/FTS5/RTree | 零部署 |
| 地图渲染 | **MapLibre GL JS** | WebGL 地图、标注碰撞、LOD | 核心渲染引擎 |
| 样式规范校验 | `@maplibre/maplibre-gl-style-spec` | 样式 JSON 校验 | 前端/构建检查 |
| 地图绘制 | **Terra Draw** + MapLibre adapter | 点/线/面编辑 | 优先于自研 |
| 样式可视化编辑 | **Maputnik** | 调色/字体/图层实验 | 可选工具 |
| 批量 GIS 编辑 | **QGIS** | 拓扑、批量属性、比例尺预览 | 可选外部工具 |
| 前端构建 | Vite + 原生 JS + JSDoc | 轻量壳，无框架 | 不使用 React/Vue |
| 属性表单 | `@json-editor/json-editor` | 由 JSON Schema 生成表单 | 优先于手写表单 |
| 测试 | pytest + Playwright（Python） | 单元/集成/E2E/截图 | 主测试语言仍是 Python |
| 质量 | Ruff + mypy + Biome | 格式/静态检查 | 单一命令 `check` |
| 字体 | Noto Sans（OFL）+ OpenMapTiles glyph PBF | 拉丁字形 | CJK 用本地字体 |
| 图标 | Maki / Temaki 等开源图标集 | POI 图标 | 记录许可证 |
| 瓦片（后续） | MBTiles / PMTiles | 性能优化 | 非 MVP 必需 |

### 4.2 开源复用清单与“不要重复造轮子”规则

| 需求 | 直接复用 | 不要自研的原因 |
|---|---|---|
| 地图渲染/缩放/标注避让 | MapLibre GL JS | 碰撞、LOD、WebGL 极其复杂 |
| 点/线/面绘制与顶点编辑 | Terra Draw | 交互状态机、撤销、选择逻辑复杂 |
| 样式可视化调参 | Maputnik | 已有成熟 MapLibre 样式编辑器 |
| 大批量绘制/拓扑检查 | QGIS | 成熟 GIS 桌面工具，Python 可扩展 |
| GeoJSON 模型/校验 | geojson-pydantic + Pydantic | 标准复杂，易漏字段 |
| 几何有效性/简化 | Shapely | 计算几何不要手写 |
| 全文搜索/空间索引 | SQLite FTS5 + R\*Tree | 内建、可靠、零部署 |
| 属性表单 | JSON Editor | 由 JSON Schema 驱动，减少重复 UI |
| 本地 HTTP/OpenAPI | FastAPI | 标准、文档自动生成 |
| 字体 glyph | OpenMapTiles fonts（Noto Sans PBF） | 避免 Windows 上编译字体工具 |
| 图标栅格化 | 开源图标 PNG 或 `sharp`/`cairosvg` | 一次性转换，不手写图形栈 |
| E2E/截图 | Playwright | 浏览器驱动、截图成熟 |
| 瓦片（如后续需要） | tippecanoe（Docker/WSL）或 PMTiles 工具 | 不要手写 tiler |

**规则**：实现任何“引擎/编辑器/切片/表单/搜索”类功能前，先在复用清单中找方案。找不到时，必须在 `docs/DECISIONS.md` 写 ADR，列出候选与不采用原因，才可自研。

### 4.3 明确避免

- **【禁止】** 用 Pyodide/PyScript 在浏览器里跑地图渲染。
- **【禁止】** 从零写 WebGL 渲染器、瓦片服务器、绘制库、表单框架。
- **【禁止】** 把 TypeScript 作为主语言；前端使用原生 ES 模块 + JSDoc 类型注解。
- **【禁止】** 引入 PostGIS/GeoServer 等重型服务；本地小地图用 SQLite。
- **【禁止】** MVP 阶段自研矢量切片；优先 GeoJSON 分级分片，必要时再用成熟工具。
- **【建议】** 不引入 React/Vue；若 UI 复杂到需要框架，先写 ADR。
- **【建议】** 不在构建期强制依赖 QGIS/PyQGIS；QGIS 仅作为外部编辑器。

### 4.4 版本与依赖策略

- 所有 Python 依赖用 `uv.lock` 锁定；所有前端依赖用 `package-lock.json` 锁定。
- Node 仅用于前端构建、样式校验、可选的字体/图标工具；运行时不依赖 Node。
- tippecanoe、QGIS、Docker 属于**外部可选工具**，由 `mapcreator doctor` 检测，不写入 Python 依赖。
- 每个新依赖写入 `docs/DEPENDENCIES.md`：用途、版本、许可证、Windows 支持、替代方案。
- 升级依赖必须单独任务，附 `check --full` 结果。
- 优先选择 **有预编译 wheel / 纯 Python / 跨平台** 的库；避免需要本机 C++ 编译链的方案。

---

## 5. 数据规范

### 5.1 坐标系与缩放

**【已定】** 使用 RFC 7946 GeoJSON 标准坐标：经度 `lon`、纬度 `lat`（EPSG:4326 语义）。

理由：tippecanoe、QGIS、Shapely、MapLibre、SQLite 工具链全部原生支持；自定义平面坐标系会破坏绝大多数开源工具的默认假设。

虚构世界处理方式（2026-11-03 确认，D-013）：

- 世界是虚构世界中的**一块有界区域**，直接使用虚构经纬度（RFC 7946 在这里只是坐标载体）；**不跨越 ±180° 经线**。
- 区域不大，**按二维俯视地图处理**：不关心纬度带来的 Web Mercator 变形，也不做投影换算。
- 因此**不设纬度限制**（不再要求 `[-60, 60]`），也不存在“接近两极”的问题。
- 世界范围优先由构建过程**从数据自动推导**（全部几何与标注的 bbox 外扩 `bounds_padding`），写入 `build/manifest.json` 供 `maxBounds`/`fitBounds` 使用；`config/world.toml` 的 `bounds` 是**可选覆盖**，仅在需要裁掉边缘数据时才填。
- `max_zoom` 固定 **17**，与最深层 kind（`hospital.default_max_zoom = 17`）对齐；`min_zoom = 0`。0.1 草案中 `max_zoom = 15` 与 kind 默认值冲突，此处已修正。
- 比例尺按 MapLibre 内置地球半径**近似显示**，仅作视觉参考，不承诺真实距离；`planet_radius_km` 保留默认 6371，不用于距离计算。

`config/world.toml` 示例（`bounds` 可省略，省略即自动推导）：

```toml
[world]
id = "aetheria"
name = "Aetheria"
# bounds 省略时由 build 从数据推导，并写入 build/manifest.json
# bounds = [-30.0, -20.0, 30.0, 20.0]
bounds_padding = 0.05        # 自动推导时向外扩的度数
# center 省略时取 bounds 中心
default_zoom = 3.0
min_zoom = 0.0
max_zoom = 17.0              # 固定 17，与最深层 kind 对齐
planet_radius_km = 6371.0    # 仅用于比例尺近似显示
default_lang = "zh"          # 主显示语言，写入 annotations.db 的 meta
```

缩放分辨率参考（Web Mercator，纬度 φ）：

```text
米/像素 ≈ 156543.03392 × cos(φ) / 2^zoom
```

该公式只作直觉参考：本项目按二维俯视处理，不用它做真实距离换算，`max_zoom` 已固定为 17（D-013）。

### 5.2 真源布局

```text
world/
├─ world.json                 # 世界元数据、图层清单、schema 版本（原 manifest.json，避免与 build/manifest.json 同名）
├─ geometry/
│  ├─ land.geojson            # 陆地/岛屿多边形
│  ├─ water.geojson           # 海洋、湖泊等多边形
│  ├─ rivers.geojson          # 河流/运河线
│  ├─ terrain.geojson         # 山脉范围/山脊线
│  ├─ roads.geojson           # 道路线
│  ├─ transit.geojson         # 地铁/公交线路几何
│  └─ parks.geojson           # 公园/保护区多边形
├─ annotations.db             # SQLite 工作库（git 忽略）
└─ annotations.sql            # 可提交的逻辑表 dump（备份/版本/diff/AI 阅读；不含 FTS/RTree 影子表）
```

标注点与几何通过 `annotation.geometry_id ↔ geojson feature.id` 关联。**名称、等级、缩放范围、图标、描述、属性只存在于 SQLite，不重复写入 GeoJSON。** 点状标注**不**生成几何要素，坐标即 `annotation.lon/lat`（D-015）。

### 5.3 GeoJSON 规范

每个文件是一个 `FeatureCollection`。要素示例：

```json
{
  "type": "Feature",
  "id": "geo.river.silverrun",
  "geometry": {
    "type": "LineString",
    "coordinates": [[-12.31, 4.52], [-11.88, 4.61], [-11.20, 4.70]]
  },
  "properties": {
    "kind": "river",
    "width_class": 2
  }
}
```

规则：

- `id` 必填，全局唯一，格式：`geo.<kind>.<slug>`；slug 使用小写字母、数字、下划线。
- `kind` 必填，必须在 `config/kinds.toml` 注册。
- `properties` 只放几何相关属性（如 `width_class`、`height_m`、`road_class`），不放 `name/rank/min_zoom` 等标注语义。
- **不写 `layer` 字段**：图层由文件名 + `world/world.json` 的图层清单唯一决定，重复写入会与真源冲突（0.1 草案示例中的 `layer` 已删除）。
- `properties` 的键与取值必须落在下表白名单内；未登记的键在 `validate` 阶段报错，不做“宽松放行”。

每个图层的几何类型与允许属性（**白名单，构建期强校验**）：

| 图层 | 文件 | 几何类型 | 允许的 `kind` | 允许的其他属性 |
|---|---|---|---|---|
| land | `land.geojson` | Polygon / MultiPolygon | `continent`、`island` | `land_class` ∈ {mainland, island} |
| water | `water.geojson` | Polygon / MultiPolygon | `ocean`、`sea`、`lake` | `water_class` ∈ {ocean, sea, lake} |
| rivers | `rivers.geojson` | LineString / MultiLineString | `river`、`canal` | `width_class` ∈ 1–5 |
| terrain | `terrain.geojson` | Polygon / LineString | `mountain_range`、`ridge` | `elev_class` ∈ 1–5 |
| roads | `roads.geojson` | LineString / MultiLineString | `road`、`street`、`trail` | `road_class` ∈ 1–5、`surface` ∈ {paved, unpaved, rail} |
| transit | `transit.geojson` | LineString / MultiLineString | `metro`、`bus`、`rail` | `mode` ∈ {metro, bus, rail}、`line_color`（`#RRGGBB`） |
| parks | `parks.geojson` | Polygon / MultiPolygon | `park`、`reserve`、`garden` | `protected` ∈ {true, false} |

其余规则：

- 坐标精度保留 **6 位小数**（约 0.1 m），构建前统一格式化。
- 多边形必须闭合、环方向正确、无自相交；默认**校验失败即中止**，`--fix` 才允许 `shapely.make_valid` 并写警告。
- 一个要素一行文本，便于 diff；由 `mapcreator format` 统一格式化。
- 每个文件建议不超过约 5 万行；超出按区域/图层拆分，并写入 `world/world.json`。

### 5.4 标注数据库（SQLite）

#### 5.4.1 表结构

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE annotation (
  fid          INTEGER PRIMARY KEY,
  id           TEXT NOT NULL UNIQUE
               CHECK (id GLOB 'anno.*.*'),        -- 粗校验；精确格式由 validate 用正则 ^anno\.[a-z_]+(\.[a-z0-9_]+)+$（D-014）
  kind         TEXT NOT NULL,
  search_text  TEXT NOT NULL DEFAULT '',         -- 由应用写入时维护：全部名称 + 描述
  parent_id    TEXT,                             -- 行政/地理父级 annotation.id
  geometry_id  TEXT,                             -- 线/面几何 id；点标注恒为 NULL（D-015）
  lon          REAL NOT NULL,                    -- 标注锚点（点标注即要素位置）
  lat          REAL NOT NULL,
  label_mode   TEXT NOT NULL DEFAULT 'point'
               CHECK (label_mode IN ('point', 'line', 'none')),
  rank         INTEGER NOT NULL DEFAULT 3 CHECK (rank BETWEEN 1 AND 5),
  min_zoom     REAL,                             -- NULL = 用 kind 的 default_min_zoom
  max_zoom     REAL,                             -- NULL = 用 kind 的 default_max_zoom
  icon         TEXT,
  description  TEXT,                             -- 世界观文本，可含 Markdown
  attrs        TEXT NOT NULL DEFAULT '{}',       -- 业务属性 JSON
  revision     INTEGER NOT NULL DEFAULT 1,
  updated_at   TEXT NOT NULL,                    -- ISO 8601 UTC
  deleted_at   TEXT,                             -- 软删除
  CHECK (min_zoom IS NULL OR max_zoom IS NULL OR min_zoom <= max_zoom)
);

-- 多语言名称与别名（D-016）。annotation 表不再有 name/name_en/aliases 列。
CREATE TABLE annotation_name (
  annotation_id TEXT NOT NULL REFERENCES annotation(id) ON DELETE CASCADE,
  lang          TEXT NOT NULL,                   -- BCP 47：zh / zh-Hant / en / ja …
  name          TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'name'
                CHECK (role IN ('name', 'alias')),
  is_primary    INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
  PRIMARY KEY (annotation_id, lang, name)
);

-- 每个标注恰好有一个主名（跨语种唯一）；主名用于列表/单语展示
CREATE UNIQUE INDEX uq_annotation_name_primary
  ON annotation_name(annotation_id) WHERE is_primary = 1;
CREATE INDEX idx_annotation_name_name ON annotation_name(name);
CREATE INDEX idx_annotation_name_lang ON annotation_name(lang);

-- 读取视图：把主名拉平，列表/搜索/导出统一走它
CREATE VIEW annotation_v AS
SELECT a.*, n.name AS name, n.lang AS name_lang
FROM annotation a
LEFT JOIN annotation_name n
  ON n.annotation_id = a.id AND n.is_primary = 1;

CREATE INDEX idx_annotation_kind     ON annotation(kind);
CREATE INDEX idx_annotation_parent   ON annotation(parent_id);
CREATE INDEX idx_annotation_geometry ON annotation(geometry_id);
CREATE INDEX idx_annotation_live     ON annotation(deleted_at) WHERE deleted_at IS NULL;

CREATE VIRTUAL TABLE annotation_rtree USING rtree(
  fid, min_lon, max_lon, min_lat, max_lat
);

CREATE VIRTUAL TABLE annotation_fts USING fts5(
  search_text,
  content='annotation',
  content_rowid='fid',
  tokenize='trigram'          -- 子串搜索；需 SQLite >= 3.34，<3 字符的查询走 LIKE 回退（D-017）
);

CREATE TABLE relation (
  id    TEXT PRIMARY KEY,
  kind  TEXT NOT NULL,        -- metro_line / bus_route / admin
  name  TEXT NOT NULL,
  attrs TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE relation_member (
  relation_id TEXT NOT NULL REFERENCES relation(id) ON DELETE CASCADE,
  member_id   TEXT NOT NULL,  -- annotation.id（stop/platform）或 geo.* 要素 id（section）
  role        TEXT NOT NULL,  -- stop / platform / section / child
  seq         INTEGER NOT NULL,
  PRIMARY KEY (relation_id, member_id, role)
);
```

FTS 与 RTree 通过触发器维护（示例）：

```sql
CREATE TRIGGER annotation_ai AFTER INSERT ON annotation BEGIN
  INSERT INTO annotation_fts(rowid, search_text) VALUES (new.fid, new.search_text);
  INSERT INTO annotation_rtree(fid, min_lon, max_lon, min_lat, max_lat)
  VALUES (new.fid, new.lon, new.lon, new.lat, new.lat);
END;

CREATE TRIGGER annotation_au AFTER UPDATE ON annotation BEGIN
  INSERT INTO annotation_fts(annotation_fts, rowid, search_text)
  VALUES ('delete', old.fid, old.search_text);
  INSERT INTO annotation_fts(rowid, search_text) VALUES (new.fid, new.search_text);
  UPDATE annotation_rtree
  SET min_lon = new.lon, max_lon = new.lon, min_lat = new.lat, max_lat = new.lat
  WHERE fid = old.fid;
END;

CREATE TRIGGER annotation_ad AFTER DELETE ON annotation BEGIN
  INSERT INTO annotation_fts(annotation_fts, rowid, search_text)
  VALUES ('delete', old.fid, old.search_text);
  DELETE FROM annotation_rtree WHERE fid = old.fid;
END;
```

实现注意：

- `search_text` 由**应用层**在写入事务内重算：所有 `annotation_name.name`（全部语种 + 别名）+ `description`。不在触发器里重算，避免 `annotation_name → annotation → FTS` 的触发器递归；`mapcreator db verify-dump` 与 `validate` 会校验它与名称表是否一致。
- 名称写入必须与 `annotation` 同事务：新增/改名/删名后 `search_text` 与 FTS 立即一致。
- `is_primary` 由应用保证“每个标注恰好一个”，DB 侧的 `uq_annotation_name_primary` 是最后防线。
- 软删除的行仍保留在 FTS/RTree 中，查询时 join 并过滤 `deleted_at IS NULL`。
- 删除/恢复通过应用层完成；不要绕开触发器直接删表行。
- 所有写入使用参数化 SQL 与事务。
- `revision` 每次更新 +1，用于乐观并发控制；名称/属性的修改同样 +1。
- `min_zoom`/`max_zoom` 为 `NULL` 时由构建期回填 kind 默认值；**不写回数据库**，保持“未显式设置”的语义。

#### 5.4.2 常用 SQL

```sql
-- 搜索（≥3 字符）：FTS5 trigram 子串匹配
SELECT a.id, a.name, a.kind, a.lon, a.lat
FROM annotation_v a
JOIN annotation_fts f ON f.rowid = a.fid
WHERE annotation_fts MATCH ?
  AND a.deleted_at IS NULL
ORDER BY a.rank ASC, a.name ASC
LIMIT 20;

-- 搜索（1–2 字符）：trigram 无法命中，回退 LIKE 扫描（2 万行内毫秒级，D-017）
SELECT a.id, a.name, a.kind, a.lon, a.lat
FROM annotation_v a
WHERE a.deleted_at IS NULL
  AND (a.name LIKE '%' || ? || '%' OR a.search_text LIKE '%' || ? || '%')
ORDER BY a.rank ASC, a.name ASC
LIMIT 20;

-- 视口查询
SELECT a.id, a.name, a.kind, a.lon, a.lat
FROM annotation_v a
JOIN annotation_rtree r ON r.fid = a.fid
WHERE r.max_lon >= ? AND r.min_lon <= ?
  AND r.max_lat >= ? AND r.min_lat <= ?
  AND a.deleted_at IS NULL;

-- 详情（多语言名称 + 属性，按 ID 回查）
SELECT a.id, a.kind, a.lon, a.lat, a.rank, a.min_zoom, a.max_zoom,
       a.description, a.attrs, a.revision, n.lang, n.name, n.role
FROM annotation a
JOIN annotation_name n ON n.annotation_id = a.id
WHERE a.id = ? AND a.deleted_at IS NULL
ORDER BY n.is_primary DESC, n.lang, n.name;

-- 属性查询
SELECT id, name, json_extract(attrs, '$.population') AS population
FROM annotation_v
WHERE kind = 'city' AND deleted_at IS NULL;
```

### 5.5 数据生命周期（含 Git 与 AI）

**【已定】** `world/annotations.db` 是运行时工作库；`world/annotations.sql` 是可提交的 SQL dump，用于版本管理、备份、diff 与 AI 阅读。

工作流：

```bash
# 从 dump 恢复工作库（新克隆/CI）
uv run mapcreator db restore --in world/annotations.sql

# 编辑后生成 dump（提交前）
uv run mapcreator db dump --out world/annotations.sql

# 导出 AI/人类友好的 JSON 快照（只读，用于阅读/调试）
uv run mapcreator annotations export --json --out build/annotations.export.json

# 从 JSON 批量导入（AI 或外部工具生成）
uv run mapcreator annotations import --json build/annotations.export.json

# 校验 dump 与工作库一致（类似 lockfile 检查）
uv run mapcreator db verify-dump --in world/annotations.sql
```

规则：

- `annotations.db` 不提交；`annotations.sql` 提交。
- SQL dump **只导逻辑表**：`meta`、`annotation`、`annotation_name`、`relation`、`relation_member`（按外键顺序）。**不导** `annotation_fts`、`annotation_rtree` 及其影子表——它们是派生索引，导入后 `restore` 自动重建（`INSERT INTO annotation_fts(annotation_fts) VALUES('rebuild')` + RTree 重填）。
- SQL dump 必须**稳定排序**（按表、主键/ID 排序），保证 diff 可读。
- 名称按 `(annotation_id, lang, role)` 排序，`is_primary` 行优先，避免改名造成整块 diff。
- `verify-dump` 除比对行数/主键外，还要校验 `search_text` 与 `annotation_name` 是否一致（D-016）。
- AI 优先通过 `mapcreator annotations ...` 的 JSON 接口读写；人工可用 SQLite 客户端做批量分析。
- 破坏性操作前先执行 `mapcreator backup`（源码 + dump 打包）。
- 构建前自动执行 `verify-dump`；不一致则失败，提示先 dump。

### 5.6 合并视图（只读）

构建生成：

- `build/unified.geojson`：几何 + 标注合并后的完整视图，供 AI/人类检查；
- `build/annotations.export.json`：纯标注快照；
- `build/manifest.json`：输入哈希、要素计数、图层统计、构建版本。

这些文件**只读**，禁止手工编辑；任何修改回到真源。

### 5.7 数据质量规则

**错误（中止构建）**：

- JSON/GeoJSON 解析失败、schema 校验失败。
- 重复 ID、非法 ID 格式（`geo.<kind>.<slug>` / `anno.<kind>.<slug>`）、未注册 `kind`。
- `geometry_id` 不存在、`parent_id` 不存在（含父子成环）、relation 成员不存在。
- 点标注（`label_mode='point'` 且 kind 为点类）却设置了 `geometry_id`；或 `label_mode='line'` 却关联到非线几何。
- 标注没有任何主名（`is_primary=1` 缺失）或主名超过一个（约束兜底）。
- 无效几何（自相交、未闭合、坐标越界）。
- `min_zoom > max_zoom`，`rank` 越界。
- 图标名不存在、必填字段缺失。

**警告（构建继续，写入报告）**：

- 陆地与水域多边形重叠、同一区域重复标注。
- 标注密度过高（某缩放带超过预算）。
- 几何未被任何标注引用（可能是遗漏）；多个标注引用同一几何（合法，但需确认不是重复录入）。
- 名称为空或全是占位符；存在 `zh` 名称但没有其他语种（提示补外文名）。
- 负面积、极短线段、重复顶点。

**拓扑**：海岸线/边界共享边、河流连通性等强拓扑检查交给 QGIS（Topology Checker），构建期只做基础有效性校验。

---

## 6. 构建管线

### 6.1 步骤

```text
1. 读取 config/ 与 world/world.json
2. 解析 GeoJSON（geojson-pydantic）
3. Shapely 校验/可选修复；坐标格式化
4. 读取 annotations.db；校验引用与唯一性
5. 合并：annotation × geometry_id → 统一要素
6. 推导默认缩放范围（kind 默认值 + 标注覆盖）
7. 生成 MapLibre 样式（base + generated + overrides）
8. 生成分级数据分片（labels / geometry by zoom band）
9. 准备图标、字体 glyph、调色板
10. 输出 build/ + manifest（哈希、计数、警告）
11. 原子发布（临时目录 → 替换 build/）
```

### 6.2 分级数据分片（MVP 核心优化）

**【已定】** MVP 不引入瓦片，使用**按缩放带预切分的 GeoJSON**：

```text
build/data/
├─ labels.z0-3.geojson
├─ labels.z4-6.geojson
├─ labels.z7-9.geojson
├─ labels.z10-12.geojson
├─ labels.z13-15.geojson
├─ lines.z7-9.geojson
├─ lines.z10-12.geojson
└─ ...
```

- 前端在缩放跨越阈值时加载/卸载对应 source；预加载相邻带，避免闪烁。
- 每个带只包含该缩放范围可见的要素，减少碰撞计算与传输量。
- 构建时对线/面按缩放带做 Shapely 简化（容差逐级减小）。
- 该方案跨 Windows、零外部工具、结果可测；**只有在性能预算被突破时才考虑瓦片**。

**带边界的权威来源（D-018 已定）**：带边界**只**由 `config/zoom_bands.toml` 定义，默认 **6 个固定带**：`z0-3 / z4-6 / z7-9 / z10-12 / z13-15 / z16-17`（最后一带覆盖 `max_zoom = 17` 的细节）。`kinds.toml` 里的 `default_min_zoom/max_zoom` **只**用于生成 style filter（带内可见性），**不参与切分**，也不反推带边界——否则改一个 kind 就会重排文件名与 golden。

```toml
# config/zoom_bands.toml
[[bands]]
name = "z0-3"
min_zoom = 0
max_zoom = 3
simplify_tolerance = 0.02      # 度；Shapely simplify(preserve_topology=True)

[[bands]]
name = "z4-6"
min_zoom = 4
max_zoom = 6
simplify_tolerance = 0.01

[[bands]]
name = "z7-9"
min_zoom = 7
max_zoom = 9
simplify_tolerance = 0.004

[[bands]]
name = "z10-12"
min_zoom = 10
max_zoom = 12
simplify_tolerance = 0.001

[[bands]]
name = "z13-15"
min_zoom = 13
max_zoom = 15
simplify_tolerance = 0.0002

[[bands]]
name = "z16-17"
min_zoom = 16
max_zoom = 17
simplify_tolerance = 0          # 不简化
```

- 文件名由 `name` 派生（`labels.<name>.geojson`），带宽数量改变只影响构建产物，不影响数据。
- 一个标注进入其 `[min_zoom, max_zoom]` 覆盖到的每一个带；带内仍用 style filter 做精确判定。
- `simplify_tolerance` 是**初始值**，M5 用实测数据调；调参需更新 golden。

### 6.3 样式生成

- `styles/base.maplibre.json`：底图（背景、陆地、水域、道路 casing、河流等），手工/Maputnik 调优。
- 由 Python 生成的图层：标注、POI、分级过滤、动态样式。
- `styles/overrides.maplibre.json`：人工覆盖项。
- 构建顺序：`base` → `generated` → `overrides` → 校验。
- 所有颜色/字号/线宽来自 `config/palette.toml` 与 `config/kinds.toml` 的语义 token，禁止在 Python 里硬编码。
- 使用 `@maplibre/maplibre-gl-style-spec` 校验最终 `build/style.json`。
- Maputnik 只用于调 base 与 overrides；不要手工编辑生成文件。

### 6.4 图标与字体

- 图标：选择开源图标集（Maki/Temaki 等），栅格化为 PNG；少于约 100 个时，前端用 `map.addImage()` 运行时加载；超过后再生成 sprite atlas。
- 字体：拉丁字符使用 Noto Sans 的预生成 glyph PBF（OpenMapTiles fonts 仓库，OFL）。
- 中文/日文/韩文：设置 MapLibre `localIdeographFontFamily: "sans-serif"`，使用系统字体，避免生成大量 CJK glyph PBF。
- 所有字体/图标附 `assets/ATTRIBUTION.md` 记录来源与许可证。

### 6.5 确定性与可重复构建

- 所有输出按稳定键排序（图层名、要素 ID、SQL 主键）。
- 坐标统一 6 位小数；JSON 使用固定缩进。
- 样式/tile/manifest 中不写入当前时间；manifest 写 `build_version`、输入哈希、工具版本。
- 构建先写 `.tmp-build/`，成功后原子替换 `build/`；失败不破坏上一次产物。
- `tests/golden/` 保存规范化后的样式、manifest 计数、标注导出、SQL dump 片段。
- 同一输入 + 同一工具版本 → 字节级一致（字体/图标二进制除外，记录哈希）。

### 6.6 命令

```bash
uv run mapcreator validate              # 只校验，不写产物
uv run mapcreator build                 # 全量构建
uv run mapcreator build --clean         # 清理后构建
uv run mapcreator build --watch         # 开发监听（watchfiles）
uv run mapcreator build --json          # 机器可读结果
```

---

## 7. 渲染与缩放分级标注

### 7.1 缩放带模型

在 `config/zoom_bands.toml` 中定义默认规则（**带边界是唯一权威**，D-018），标注可覆盖：

| 缩放范围 | 内容示例 | 默认 rank |
|---|---|---|
| z0–3 | 大陆、大洋、主要山脉 | 1 |
| z4–6 | 国家/区域、主要城市 | 1–2 |
| z7–9 | 城市、河流、主要道路 | 2–3 |
| z10–12 | 区、公园、车站、主要 POI | 3–4 |
| z13–15 | 医院、学校、小 POI | 4–5 |
| z16–17 | 建筑级细节、站点出入口 | 5 |

规则：

- 每个 `kind` 在 `config/kinds.toml` 中定义 `default_min_zoom`、`default_max_zoom`、`default_rank`。
- `annotation.min_zoom/max_zoom` 为 `NULL` 时使用 kind 默认值；显式值优先。
- `rank` 同时影响字号、图标优先级与碰撞排序。
- kind 的缩放区间与带边界**不必对齐**：`min_zoom=8.5` 合法，构建时按带内覆盖关系分配，带内再由 style filter 精确判定。
- 不为“缩放”写魔法公式；所有阈值表格化、可读、可测试。

字号与图标尺寸（**初始值**，由 `config/palette.toml` 的 token 驱动，M1 调参后更新 golden）：

| rank | 文字字号（z7–12） | 文字字号（z13–17） | 图标边长 |
|---|---|---|---|
| 1 | 18 | 20 | — |
| 2 | 15 | 17 | 20 |
| 3 | 13 | 15 | 18 |
| 4 | 12 | 14 | 16 |
| 5 | 11 | 13 | 14 |

`config/kinds.toml` 示例：

```toml
[kinds.city]
label_mode = "point"
default_rank = 2
default_min_zoom = 4.0
default_max_zoom = 13.0
icon = "city"
color_token = "label.city"
attrs_schema = "schemas/kinds/city.schema.json"

[kinds.hospital]
label_mode = "point"
default_rank = 4
default_min_zoom = 12.0
default_max_zoom = 17.0
icon = "hospital"
color_token = "label.health"
attrs_schema = "schemas/kinds/hospital.schema.json"

[kinds.river]
label_mode = "line"
default_rank = 3
default_min_zoom = 5.0
default_max_zoom = 14.0
```

> 完整首批注册表见 §7.6；上例三个 kind 的数值必须与 §7.6 一致（`validate` 会比对）。

### 7.2 碰撞与优先级

- 点标注：一个或少量 symbol layer，`symbol-sort-key = rank`（数值越小越优先），`text-allow-overlap: false`。
- 线标注：独立 symbol layer，`symbol-placement: line`，按 rank 排序。
- POI 图标 + 文字：使用 `text-variable-anchor`、`text-padding`、`icon-allow-overlap` 控制密度。
- 跨 symbol layer 的碰撞由样式层顺序与排序键共同决定；高优先级图层放在前面，并用测试验证。
- 每缩放带控制可见标注数量（建议 ≤ 3000），超出时优先裁剪低 rank 要素或按区域拆分。
- 不使用 DOM marker 渲染成千上万个点；全部使用 symbol layer。

### 7.3 视觉规则

- 字号、光晕、颜色、图标大小由 rank + zoom 插值表达式生成。
- 地形：面状范围 + 山峰图标/高程文字；**不做 hillshade/DEM**（§18.1 第 6 条，M5 之后再议）。
- 河流：按 `width_class` 分级线宽；湖泊为水面多边形。
- 道路：按 `road_class` 分级线宽与 casing。
- 轨道交通：按线路颜色/模式渲染；站点在高缩放级别显示。
- 标注锚点可编辑：面/线要素的标签锚点就是 annotation 点，允许人工拖动以优化位置。

### 7.4 交互

- 点击：`queryRenderedFeatures` → 打开详情面板；`promoteId` 使用**标注/几何 ID**，用 `feature-state` 做选中高亮。
- 搜索：输入 → `/api/search` → 结果列表 → `flyTo` + 高亮。
- URL 状态：`#z=6&lat=..&lon=..&sel=anno.city.silverrun`（`sel` 为标注 ID，见 D-014），便于分享与自动化测试。
- 多语言显示：`#lang=zh,en` 控制标签语种顺序与是否叠加显示；缺省用 `config/world.toml` 的 `default_lang`（D-016/D-020）。
- SQL 过滤（高级）：只读查询 → 返回 ID 列表 → 高亮图层。
- 图层开关：由 kinds 分组生成，状态保存到 localStorage。

### 7.5 性能策略

优先级从低到高：

1. 构建期按缩放带裁剪要素。
2. 构建期几何简化。
3. 前端预加载相邻缩放带。
4. 限制每带标注数量。
5. 若仍超预算：引入瓦片（见 15 节风险与 19 节决策）。

### 7.6 MVP kind 注册表（首批）

0.1 草案只给了 `city`/`hospital`/`river` 三个示例，没有全集。以下为 M0 写入 `config/kinds.toml` 的**首批注册表**；新增 kind 必须同时补 `schemas/kinds/<kind>.schema.json`、图标与调色板 token。

| 组 | kind | label_mode | rank | min_zoom | max_zoom | 说明 |
|---|---|---|---|---|---|---|
| 自然 | `continent` | point | 1 | 0 | 8 | 大陆 |
| 自然 | `ocean` | point | 1 | 0 | 7 | 大洋 |
| 自然 | `sea` | point | 2 | 3 | 9 | 海、海湾 |
| 自然 | `lake` | point | 3 | 8 | 14 | 湖泊 |
| 自然 | `island` | point | 3 | 5 | 12 | 岛屿 |
| 自然 | `mountain_range` | point | 2 | 2 | 9 | 山脉 |
| 自然 | `peak` | point | 3 | 6 | 15 | 山峰 |
| 自然 | `river` | line | 3 | 5 | 14 | 河流（关联 `rivers.geojson`） |
| 自然 | `forest` | point | 4 | 8 | 14 | 森林 |
| 人文 | `country` | point | 1 | 2 | 8 | 国家 |
| 人文 | `region` | point | 2 | 3 | 10 | 区域/行省 |
| 人文 | `city` | point | 2 | 4 | 13 | 城市 |
| 人文 | `town` | point | 3 | 8 | 15 | 城镇 |
| 人文 | `village` | point | 4 | 10 | 17 | 村庄 |
| 人文 | `district` | point | 4 | 10 | 17 | 城区 |
| 人文 | `park` | point | 4 | 10 | 17 | 公园（关联 `parks.geojson`） |
| 交通 | `metro_line` | line | 3 | 9 | 15 | 地铁线（关联 `transit.geojson`） |
| 交通 | `road` | line | 4 | 9 | 15 | 道路（关联 `roads.geojson`） |
| 交通 | `station` | point | 4 | 11 | 17 | 车站 |
| 交通 | `airport` | point | 4 | 10 | 17 | 机场 |
| 交通 | `port` | point | 4 | 10 | 17 | 港口 |
| 设施 | `hospital` | point | 4 | 12 | 17 | 医院 |
| 设施 | `school` | point | 4 | 12 | 17 | 学校 |
| 设施 | `university` | point | 4 | 12 | 17 | 大学 |
| 设施 | `museum` | point | 5 | 13 | 17 | 博物馆 |
| 设施 | `temple` | point | 5 | 13 | 17 | 寺庙/教堂 |
| 设施 | `market` | point | 5 | 13 | 17 | 集市 |

- 上表数值即 **kind 默认值**；单个标注可在 `annotation.min_zoom/max_zoom/rank` 覆盖。
- `label_mode = "line"` 的 kind 必须关联线几何；`label_mode = "point"` 的 kind 一律 `geometry_id = NULL`（D-015）。
- 图标只需为 point 类 kind 提供；`continent/ocean/sea` 等大面积名称用纯文字、无图标。

---

## 8. 编辑器

### 8.1 策略

| 方案 | 用途 | 决策 |
|---|---|---|
| Web 编辑器（Terra Draw） | 日常点/线/面/标注编辑 | **MVP 必做** |
| QGIS | 批量绘制、拓扑检查、海岸线/边界精修 | **可选**（不安装也能完成 MVP） |
| 自研桌面编辑器 | 产品化 | 暂不做；需要时先 ADR |

### 8.2 Web 编辑器功能

- 工具：选择、点、线、多边形、矩形、自由绘制；顶点编辑。
- 撤销/重做：优先使用 Terra Draw 自带能力；实现前核对锁定版本 API。
- 属性表单：基础字段（**多语言名称**、rank、min/max zoom、描述）单独渲染；业务属性由 `attrs_schema` + JSON Editor 生成。
- 工具与数据的对应关系（D-015）：**点**工具直接创建标注（含 `lon/lat`），不生成 GeoJSON 几何；**线/面**工具先写几何要素，再可选地创建/关联一个标注。
- 删除几何时若仍有标注引用 → 返回 409 并列出引用者；显式 `--cascade` 才连同标注一起软删。
- 保存：一次提交一个或多个要素；服务端校验后写入；返回逐要素错误。
- 软删除 + 恢复；删除需确认。
- 并发：`revision` 乐观锁；单用户场景冲突概率低，但必须检测。
- 捕捉/拓扑：Web 端能力有限；海岸线、国界等强拓扑数据用 QGIS。
- 新建 ID：服务端生成 `geo.<kind>.<slug>` / `anno.<kind>.<slug>`（D-014），确保唯一；用户可改名称与 slug，但**ID 不变**。

**【禁止】** 浏览器直接写 GeoJSON 文件或 SQLite；必须走 FastAPI 写入接口。

### 8.3 QGIS 工作流

1. `mapcreator export --qgis` 导出：
   - `build/qgis/geometry/*.geojson`
   - `build/qgis/annotations.geojson`（点 + 全部字段；`attrs` 中为业务属性 JSON，`names` 中为多语言名称 JSON，见 D-016）
2. QGIS 打开图层，设置 CRS `EPSG:4326`；可配置按比例尺显示与标注规则预览。
3. 编辑后保存为同路径 GeoJSON。
4. `mapcreator geometry import --dir build/qgis/geometry` / `mapcreator annotations import --geojson build/qgis/annotations.geojson`。
5. 服务端校验、更新 revision、重新构建。

注意：

- QGIS 是 GPL 软件，作为**独立外部工具**使用，不链接进本项目；分发时不捆绑 QGIS。
- QGIS 可能重排 GeoJSON 文本；导入后用 `mapcreator format` 规范化，减少 diff 噪音。
- 强拓扑数据（海岸线共享边）用 QGIS Topology Checker；构建期只做基础校验。

### 8.4 编辑数据流

```text
客户端/QGIS
   │ JSON / GeoJSON
   ▼
FastAPI / CLI（唯一写入口）
   │ Pydantic 校验 + Shapely 校验 + 引用检查 + revision 检查
   ▼
真源（GeoJSON / SQLite 事务）
   │
   ▼
增量构建（样式/分片/manifest）
   │
   ▼
客户端刷新 / 文件监听
```

### 8.5 安全与并发

- 默认单用户、单进程 Uvicorn worker。
- SQLite WAL，写事务串行。
- 校验 `Origin`/`Host` 防止本地 CSRF；可选启动 token。
- 只读 SQL 接口：仅允许 `SELECT`/`WITH`，使用只读连接、超时、行数限制；默认关闭，显式 `--enable-sql` 开启。
- 文件写入使用临时文件 + `os.replace`；构建使用原子目录替换。

### 8.6 HTTP API 契约（MVP 清单）

0.1 草案只提到 `/api/search` 一个端点，其余靠猜。以下为 **M0 起冻结的端点清单**；新增端点需更新本节 + `docs/openapi.json`。

| 方法 | 路径 | 用途 | 模式 |
|---|---|---|---|
| GET | `/api/health` | 存活、版本、`build_id` | 只读 |
| GET | `/api/world` | 世界元数据、kind 注册表、缩放带、bounds | 只读 |
| GET | `/api/data/{band}` | 取某缩放带的渲染分片（也可直接走静态文件） | 只读 |
| GET | `/api/annotations/{id}` | 详情：全部名称、描述、attrs、链接的 geometry_id | 只读 |
| GET | `/api/search?q=&lang=&limit=` | FTS + 短词 LIKE 回退（D-017） | 只读 |
| GET | `/api/map/{bbox}?zoom=` | 视口查询（RTree），返回 **id 列表** | 只读 |
| POST | `/api/query` | 只读 SQL，默认关闭（`--enable-sql`） | 只读 |
| POST | `/api/annotations` | 新建标注（含名称数组） | 编辑 |
| PATCH | `/api/annotations/{id}` | 更新（必须带 `revision`） | 编辑 |
| DELETE | `/api/annotations/{id}` | 软删除（`?restore=true` 恢复） | 编辑 |
| POST | `/api/geometry` | 新建或更新线/面要素（GeoJSON + `revision`） | 编辑 |
| DELETE | `/api/geometry/{id}` | 删除几何；被引用时 409（`?cascade=true` 才级联） | 编辑 |
| POST | `/api/build` | 触发增量构建（仅 `--dev`） | 编辑 |

约定：

- **载荷以 ID 为主**：除 `/api/search` 与 `/api/annotations/{id}` 外，响应只给 `id` 与渲染必需字段（渲染分片额外带 `name`，见 D-016）。
- 列表类响应统一 `{ "items": [...], "total": n }`；单对象直接返回对象。
- 写接口统一要求 `If-Match: <revision>` 或 body 中的 `revision`，冲突返回 409 + `code: "REVISION_CONFLICT"`。
- 错误体沿用 §9.5 的 `code/message/path/feature_id/details/remediation`。
- 编辑类端点仅在 `--enable-edit` 下注册；未开启时返回 404（不泄露能力）。

---

## 9. 本地应用与运行

### 9.1 前置条件

| 依赖 | 必需 | 用途 |
|---|---|---|
| Python 3.12+ | 是 | 后端/构建/CLI |
| uv | 是 | Python 环境与依赖 |
| Node.js 20 LTS+ | 是（构建前端） | Vite/Biome/样式校验 |
| 现代浏览器（Edge/Chrome/Firefox） | 是 | WebGL2 渲染 |
| QGIS | 否 | 批量/拓扑编辑 |
| Docker 或 WSL | 否 | 后续 tippecanoe 切片 |

AI Agent 不要求人类手动执行项目内步骤；只可能要求人类安装上述系统级前置条件。

### 9.2 命令

```bash
# 环境自检（JSON 输出，含修复建议）
uv run mapcreator doctor --json

# 安装/构建前端与依赖（幂等）
uv run mapcreator setup

# 校验数据
uv run mapcreator validate

# 构建产物
uv run mapcreator build

# 启动本地应用（默认 127.0.0.1:8765）
uv run mapcreator serve

# 开发模式：监听变更 + 自动重建
uv run mapcreator serve --dev

# 全部质量检查（供 AI 使用）
uv run mapcreator check --full --json

# 导出只读静态站点（M5 之后，D-019；MVP 不实现）（M5 之后，见 D-019；MVP 不实现）
uv run mapcreator export --static --out dist/

# 生成 API 契约
uv run mapcreator openapi --out docs/openapi.json
```

### 9.3 运行模式

- **Read-only**：默认；只读数据与搜索。
- **Edit**：显式 `--enable-edit`；开启编辑 API 与 Web 编辑器。
- **Static export**：无服务端、只读；复制 `web/dist` + `build/data`，用任意静态 HTTP 服务打开。**MVP 不实现，推迟到 M5 之后（D-019）**。
- **Dev**：watchfiles 监听 `world/`、`config/`、`web/src/`，重建并刷新提示。

### 9.4 配置与端口

- 配置文件：`config/world.toml`、`config/kinds.toml`、`config/zoom_bands.toml`、`config/palette.toml`。
- 环境变量仅用于敏感/环境相关项（如端口、数据目录），默认值写入文档。
- 默认 `127.0.0.1:8765`；禁止默认绑定 `0.0.0.0`。
- 单进程 Uvicorn；不使用多 worker。

### 9.5 日志与错误

- CLI 人类模式：简洁可读；`--json` 模式：结构化 JSON。
- 日志写 `logs/app.jsonl`（git 忽略）；包含时间、级别、事件、要素 ID。
- API 错误统一样式：

```json
{
  "code": "GEOMETRY_INVALID",
  "message": "Polygon is self-intersecting",
  "path": "world/geometry/parks.geojson",
  "feature_id": "geo.park.central",
  "details": {"reason": "Self-intersection at ..."},
  "remediation": "Run mapcreator validate --fix or edit in QGIS"
}
```

- 退出码：`0` 成功；`1` 数据/校验失败；`2` 用法/配置错误；`3` 环境/依赖缺失；`4` 内部错误。

### 9.6 Windows 注意事项

- 代码统一使用 `pathlib.Path`，所有文件读写显式 `encoding="utf-8"`（无 BOM）。
- 不使用 `make`/bash 专用语法作为构建入口；一律 `uv run mapcreator ...`。
- tippecanoe 原生 Windows 支持有限；MVP 不需要。后续优先 Docker/WSL，或经 ADR 后用纯 Python 方案。
- 避免依赖需要本机编译的 Node 原生模块；字体/图标使用预生成资产。
- 文件可能被杀毒软件占用；写入使用重试 + 原子替换。
- 路径大小写不敏感：禁止仅靠大小写区分的文件名。
- `.gitattributes` 统一 `text=auto eol=lf`，二进制资产单独标记。
- 数据库 WAL 文件（`-wal`/`-shm`）不提交，备份时用 SQLite backup API。

---

## 10. AI Agent 开发协议

本节是“AI 可读性”的核心。所有 AI Agent 必须遵守；人类评审也以此为依据。

### 10.1 仓库即上下文

开发启动后必须在仓库根目录创建：

| 文件 | 长度目标 | 内容 |
|---|---|---|
| `AGENTS.md` | ≤ 200 行 | 唯一入口：命令、阅读顺序、规则、DoD、禁止事项 |
| `CLAUDE.md` | 1–3 行 | 仅指向 `AGENTS.md`（Claude Code 兼容） |
| `docs/ARCHITECTURE.md` | ≤ 200 行 | 架构、数据流、模块职责 |
| `docs/DATA_SPEC.md` | ≤ 250 行 | 坐标、schema、SQL、校验规则 |
| `docs/EDITOR.md` | ≤ 150 行 | Web 编辑器与 QGIS 流程 |
| `docs/TESTING.md` | ≤ 150 行 | 测试策略与命令 |
| `docs/DEPENDENCIES.md` | 表格 | 依赖、版本、许可证、Windows 支持 |
| `docs/DECISIONS.md` | 追加 | ADR |
| `docs/STATUS.md` | ≤ 80 行 | 当前里程碑、已知问题、下一步、最近证据 |

规则：

- 文档之间用**路径链接**，不复制大段内容。
- 每个事实只写一处；其他地方引用。
- 文档中的命令必须真实可执行；`check` 包含“文档命令冒烟测试”（至少检查命令存在）。
- 每完成一个任务更新 `STATUS.md`；每个架构决策追加 `DECISIONS.md`。

### 10.2 单一入口命令

AI 只通过这些命令工作（底层可调用 npm/Docker/QGIS）：

```bash
uv run mapcreator doctor --json       # 环境/能力/修复建议
uv run mapcreator describe --json     # 世界概览：范围、kind、计数、版本
uv run mapcreator validate --json
uv run mapcreator build --json
uv run mapcreator serve               # 人工/截图时使用
uv run mapcreator check --full --json # 格式/类型/单测/校验/构建/E2E
uv run mapcreator screenshot --url "..." --out artifacts/shot.png
uv run mapcreator query --sql "SELECT ..." --json
uv run mapcreator export --static --out dist/
uv run mapcreator openapi --out docs/openapi.json
```

要求：

- 所有命令支持 `--json`，输出稳定字段：`ok`、`command`、`duration_ms`、`errors[]`、`warnings[]`、`artifacts[]`。
- 稳定退出码（见 9.5）。
- 错误包含路径、要素 ID、修复建议。
- 不在交互式提示中阻塞 AI；需要确认的危险操作使用 `--yes` 显式传入。

### 10.3 标准任务循环

1. **读取**：`AGENTS.md` → 相关 docs → 当前 `tasks/TASK-xxxx.md`。
2. **自检**：`uv run mapcreator doctor --json`。
3. **计划**：列出将修改的文件、验收测试、风险；若任务含歧义，先提问。
4. **实现**：小而完整的垂直切片；不夹带无关重构。
5. **验证**：`uv run mapcreator check --json`；UI 变更必须截图并自行查看。
6. **记录**：更新 `STATUS.md`；重大决策写 ADR；新依赖写 `DEPENDENCIES.md`。
7. **报告**：摘要、修改文件、命令与结果、证据路径、已知问题、下一步。

### 10.4 Definition of Done（DoD）

- [ ] 行为已实现，且有对应测试（单元/集成/E2E 至少一种）。
- [ ] `uv run mapcreator check --full --json` 通过。
- [ ] schema/数据/API 变更已同步文档与 golden 文件。
- [ ] DB 变更包含迁移、`schema_version` 更新、备份说明。
- [ ] UI 变更附带截图（并由 AI 查看确认）。
- [ ] 性能未超出预算；若超预算，有测量数据与 ADR。
- [ ] 未新增未登记依赖；许可证已记录。
- [ ] 未手工编辑生成文件；未提交 `build/`、`dist/`、DB、截图 artifacts。
- [ ] `docs/STATUS.md` 已更新；重大决策已写 ADR。
- [ ] 错误信息包含路径/ID/修复建议。

### 10.5 证据要求

AI 不得只说“已完成”。必须提供：

- 执行的命令与关键输出（可截断，但保留结论）。
- 变更文件列表。
- UI：截图路径（AI 必须读取并检查）。
- 数据：manifest 计数/哈希、校验输出。
- 性能：`artifacts/perf.json` 或基准输出。
- 若未验证某点，明确写出“未验证及原因”。

### 10.6 依赖与“不要造轮子”规则

引入或自研前：

1. 查第 4.2 节复用清单。
2. 检查候选库：维护状态、许可证、Windows wheel、与锁定版本兼容性。
3. 优先纯 Python / 有预编译包的方案。
4. 新依赖必须：
   - 锁定版本；
   - 在 `docs/DEPENDENCIES.md` 登记；
   - 至少一个导入/使用冒烟测试；
   - 不引入两个功能重复的库。
5. 自研引擎/编辑器/切片/表单/搜索前必须写 ADR，说明为何现有项目不适用。

### 10.7 文档规则

- **Spec-first**：先改 schema/契约，再改实现。
- 文档短、链接多、命令可复制。
- ADR 模板：

```markdown
# ADR-0001: 标题

- Status: proposed | accepted | superseded by ADR-XXXX
- Date: YYYY-MM-DD
- Context: 问题与约束
- Decision: 选择
- Consequences: 正面/负面/后续
- Alternatives considered: 候选与未采用原因
```

- `STATUS.md` 模板：

```markdown
# Status

- 当前里程碑：M1
- 最近更新：YYYY-MM-DD
- 已完成：...
- 已知问题：...
- 下一步：...
- 最近证据：命令/截图路径
```

### 10.8 代码可读性约定

**Python**

- 全量类型注解；公共函数有 docstring（说明契约，而非复述代码）。
- 小而纯的转换函数；副作用集中在 CLI/API 边界。
- 模块职责单一；单文件建议 < 300 行。
- 不用隐式全局状态；配置显式传入。
- 自定义异常带 `code`、`path`、`feature_id`、`remediation`。
- 优先标准库；性能热点再引入加速库。
- 所有外部命令用 `subprocess.run([...], check=True)`，不拼 shell 字符串。

**JavaScript**

- 原生 ES 模块；文件顶部 `// @ts-check`，使用 JSDoc 类型。
- Biome 统一格式与 lint；不引入框架（除非 ADR）。
- `main.js` 只做启动；`map.js` 管地图；`api.js` 管请求；`editor.js` 管绘制；`ui.js` 管面板。
- 暴露 `window.__app`（仅测试模式）用于 E2E 断言，如 `ready`、`zoom`、`visibleLabelCount`。
- 不把业务逻辑放进 HTML；不在前端做数据校验的“唯一防线”。

**数据**

- ID 稳定、可读、全局唯一。
- 单位显式（`height_m`、`population`），不依赖上下文。
- 输出稳定排序、固定精度。
- 生成文件顶部写 `GENERATED — DO NOT EDIT`。

### 10.9 任务文件模板

```markdown
# TASK-0001: 标题

- Status: pending | in_progress | done | blocked
- Milestone: M1
- Owner: AI Agent
- Context: 相关 docs/文件链接
- Goal: 一句话
- Scope: 允许修改的范围
- Out of scope: 明确不做
- Acceptance criteria:
  - [ ] ...
  - [ ] ...
- Evidence required: 命令/测试/截图
- Dependencies: 无 / TASK-xxxx
- Notes: 风险与假设
```

### 10.10 常用 Prompt 模板

**实现任务**

```text
阅读 AGENTS.md、docs/ARCHITECTURE.md、docs/DATA_SPEC.md 和 tasks/TASK-0007.md。
先运行 uv run mapcreator doctor --json。
按任务验收标准实现；不要修改范围外文件。
完成后运行 uv run mapcreator check --full --json。
如有 UI 变更，用 Playwright 截图并自行查看，把截图路径写进报告。
更新 docs/STATUS.md；若做了架构决策，追加 ADR。
报告：摘要、文件、命令输出、截图、风险、未验证项。
```

**代码评审**

```text
以严格评审者身份检查当前变更：
1. 是否符合 AGENTS.md 与 DATA_SPEC；
2. 是否有重复造轮子；
3. 测试是否覆盖边界与错误路径；
4. 是否破坏确定性/性能预算；
5. 文档与 schema 是否同步。
按严重级别列出问题，引用文件:行号，不要泛泛而谈。
```

**数据生成**

```text
根据 schemas/ 与 config/kinds.toml 生成一份符合规范的 GeoJSON/标注 JSON。
要求：ID 唯一、坐标 6 位小数、几何有效、标注引用存在、rank/zoom 合理。
生成后运行 uv run mapcreator validate --json，修正所有错误后再报告。
```

**视觉问题调试**

```text
启动 uv run mapcreator serve，使用 Playwright 打开指定 URL（含 z/lat/lon），
截图到 artifacts/，检查标注是否按缩放带显示、是否碰撞、是否有缺失。
对比 build/manifest.json 的计数与页面可见要素数，给出根因与修复方案。
```

### 10.11 多 AI 协作

- 人类是最终裁决者；`DECISIONS.md` 是共同记忆，禁止反复推翻已接受决策。
- 同一时间一个 Agent 负责一个任务/文件区域；并行时使用独立 git worktree/branch。
- 评审 Agent 按 DoD + 第 10.8 节检查；实现 Agent 不自行“宣布通过”。
- 冲突时以文档中的 **【已定】** 为准；需要变更时先提 ADR。

### 10.12 可读性验收指标

- 新 AI Agent 在 10 分钟内可以：读文档 → `doctor` → `check` → 启动应用 → 截图。
- 核心上下文（AGENTS + ARCHITECTURE + DATA_SPEC + 当前任务）≤ 600 行。
- 每个命令都有 `--help` 与 `--json`。
- 每个错误都可定位到文件/要素，并给出下一步。
- 每个产物都有 manifest 或 golden 文件。
- 不依赖口头知识、隐含约定、手工步骤。

### 10.13 AI 反模式（禁止）

- 编造库 API；必须先查锁定版本的文档/类型/源码。
- 修改生成文件后声称“修好了”。
- 为小功能引入大框架。
- 手工维护巨大的 style JSON。
- 把状态只放在浏览器内存/局部存储。
- 静默吞异常或只打印 “error”。
- 构建输出包含时间戳导致不可重复。
- 未经 ADR 自研地图引擎/编辑器/切片器。
- 跳过截图/测试就报告完成。

---

## 11. 仓库结构

```text
MapCreator/
├─ AGENTS.md                     # 开发启动后创建（AI 入口）
├─ CLAUDE.md                     # 指向 AGENTS.md
├─ README.md
├─ DEVELOPMENT_PREP.md           # 本文档
├─ pyproject.toml
├─ uv.lock
├─ package.json
├─ package-lock.json
├─ biome.json
├─ .gitignore
├─ .gitattributes
├─ config/
│  ├─ world.toml
│  ├─ kinds.toml
│  ├─ zoom_bands.toml
│  └─ palette.toml
├─ schemas/
│  ├─ geometry.schema.json
│  ├─ annotation.schema.json
│  ├─ annotation-name.schema.json
│  ├─ style-input.schema.json
│  └─ kinds/
│     ├─ city.schema.json
│     └─ hospital.schema.json
├─ world/
│  ├─ world.json                # 世界元数据、图层清单、schema 版本
│  ├─ geometry/
│  │  ├─ land.geojson
│  │  ├─ water.geojson
│  │  ├─ rivers.geojson
│  │  ├─ terrain.geojson
│  │  ├─ roads.geojson
│  │  ├─ transit.geojson
│  │  └─ parks.geojson
│  ├─ annotations.db            # 工作库，git 忽略
│  └─ annotations.sql           # 逻辑表 dump，提交
├─ assets/
│  ├─ icons/
│  ├─ fonts/
│  └─ ATTRIBUTION.md
├─ styles/
│  ├─ base.maplibre.json
│  └─ overrides.maplibre.json
├─ src/mapcreator/
│  ├─ __init__.py
│  ├─ cli.py
│  ├─ config.py
│  ├─ models.py
│  ├─ errors.py
│  ├─ db/
│  │  ├─ schema.sql
│  │  ├─ migrations/
│  │  └─ repo.py
│  ├─ data/
│  │  ├─ geometry.py
│  │  └─ annotations.py
│  ├─ build/
│  │  ├─ pipeline.py
│  │  ├─ style.py
│  │  ├─ bands.py
│  │  ├─ assets.py
│  │  └─ manifest.py
│  ├─ server/
│  │  ├─ app.py
│  │  ├─ routes.py
│  │  └─ static.py
│  └─ qgis/
│     └─ roundtrip.py
├─ web/
│  ├─ index.html
│  ├─ src/
│  │  ├─ main.js
│  │  ├─ map.js
│  │  ├─ api.js
│  │  ├─ editor.js
│  │  ├─ search.js
│  │  └─ ui.js
│  ├─ i18n/                     # 界面文案：zh.json 必做；en.json 预留（不引框架，D-020）
│  └─ dist/                     # git 忽略
├─ build/                       # git 忽略
├─ artifacts/                   # 截图/性能报告，git 忽略
├─ docs/
│  ├─ ARCHITECTURE.md
│  ├─ DATA_SPEC.md
│  ├─ EDITOR.md
│  ├─ TESTING.md
│  ├─ DEPENDENCIES.md
│  ├─ DECISIONS.md
│  ├─ STATUS.md
│  └─ openapi.json              # 生成后提交，供 AI 读取
├─ tasks/
│  └─ TASK-0001-template.md
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ e2e/
│  ├─ golden/
│  └─ fixtures/mini-world/
└─ .github/workflows/check.yml  # 可选
```

`tests/fixtures/mini-world/` 提供最小样例：1 块大陆、1 片海、2 条河、1 条山脉、2 座城、5 个 POI、1 条地铁线。所有 golden/E2E 基于它，避免测试依赖真实世界数据。

---

## 12. 里程碑与首批任务

### 12.1 里程碑

| 里程碑 | 交付物 | 验收标准 |
|---|---|---|
| **M0 骨架与契约** | 仓库结构、`AGENTS.md`、CLI 骨架、config、schema、mini-world、`doctor`/`check`、Web 构建 | `doctor` 全绿；`check` 通过；`serve` 显示一个可缩放样例 |
| **M1 浏览与分级标注** | 构建合并视图、MapLibre 页面、缩放带、点/线标注、碰撞、点选详情、URL 状态 | z0→z15 缩放正常；标注按规则出现/消失；无控制台错误 |
| **M2 搜索与 SQL** | FTS5/RTree、搜索 API/UI、只读 SQL 过滤、标注导入导出、dump/restore | 中文/英文/别名可搜；结果可定位；dump 往返一致 |
| **M3 编辑器** | Terra Draw 点/线/面/标注编辑、属性表单、保存校验、撤销/重做、软删除 | 创建/编辑/删除三类几何 + 标注；非法输入被拒绝；编辑后刷新可见 |
| **M4 交通与数据运维** | relation、地铁/公交线路与有序站点、QGIS 导出/导入、批量导入、审计日志 | 创建 5 站线路并渲染；QGIS 往返不丢字段；批量导入校验完整 |
| **M5 性能与分发** | 分级分片优化、简化、可选 PMTiles、性能基准、打包说明（静态导出见 D-019，排在 M5 之后） | 性能预算达标；文档完整 |

### 12.2 首批任务（按顺序）

1. **TASK-0001 仓库骨架**：目录、`pyproject.toml`、`uv`、Vite、Biome、Ruff、mypy、`.gitignore`、`.gitattributes`、`AGENTS.md`、`CLAUDE.md`。
2. **TASK-0002 CLI 与 doctor**：Typer 入口、`doctor`、统一 JSON 输出、退出码、环境检查（Python/Node/SQLite FTS5/RTree/Playwright/QGIS）。
3. **TASK-0003 配置与 schema**：`config/*.toml`、Pydantic 模型、JSON Schema 导出、mini-world。
4. **TASK-0004 数据库层**：schema、迁移、仓库类、`annotation_name` 多语言名称、dump/restore/verify、标注 CRUD、FTS/RTree 触发器。
5. **TASK-0005 构建合并**：几何 + 标注 join、默认 zoom、统一 GeoJSON、manifest、原子发布。
6. **TASK-0006 样式与前端地图**：样式生成、MapLibre 页面、缩放带加载、点/线标注、碰撞调优。
7. **TASK-0007 搜索**：搜索 API、搜索 UI、flyTo/高亮、只读 SQL 过滤。
8. **TASK-0008 编辑器**：Terra Draw 集成、JSON Editor 表单、保存 API、撤销/重做、软删除。
9. **TASK-0009 测试与证据**：单测、golden、Playwright E2E、截图、性能基准、`check --full`。
10. **TASK-0010 QGIS 往返 + 文档收尾**：导出/导入、格式化、QGIS 指南、`STATUS.md`/ADR 完善。

---

## 13. 测试与质量门禁

### 13.1 测试层级

| 层级 | 内容 | 工具 |
|---|---|---|
| 单元 | schema、ID、zoom 推导、样式生成、DB CRUD、搜索 | pytest |
| 集成 | mini-world 构建、导入导出、dump/restore、API | pytest + httpx |
| Golden | 规范化 style、manifest 计数、标注导出、SQL dump | pytest |
| E2E | 加载、缩放、标注出现、搜索、编辑、保存 | pytest + Playwright |
| 视觉 | 固定视口/URL 截图，供 AI/人类检查 | Playwright |
| 性能 | 构建时间、加载时间、标注数、内存 | Playwright metrics + 计时 |
| 数据质量 | 全量校验、警告统计 | `mapcreator validate` |

**必须覆盖的边界用例**（本节补充，任一缺失视为测试不完整）：

- 搜索：1 字符、2 字符（`上海`）、3 字符、纯英文、别名、含空格与标点、跨语种命中同一标注。
- 多语言：只有 `zh` 的标注、`zh+en` 双语、第三语种；`is_primary` 缺失/重复被拒绝。
- 点标注带 `geometry_id` 被拒绝；线标注关联面几何被拒绝。
- 缩放带交界（`z3→z4`、`z6→z7`）：标注不重复、不闪断、计数与 manifest 一致。
- `min_zoom/max_zoom` 为 `NULL` 时回填 kind 默认值，且不写回库。
- 删除仍被引用的几何 → 409；`--cascade` → 软删并可恢复。
- 并发写入：陈旧 `revision` → 409，不产生脏写。
- dump/restore 往返：逻辑表字节级一致，FTS/RTree 重建后搜索结果一致。

### 13.2 视觉测试策略

- WebGL 无头截图跨 GPU/OS 可能有像素差异；**初期不做严格像素断言**。
- 截图保存到 `artifacts/`，AI 必须读取并检查以下项：
  - 地图是否加载；
  - 缩放带标注是否出现/消失；
  - 是否有明显重叠/空洞；
  - 中文是否正常显示（`localIdeographFontFamily` 生效，无方块字）；
  - 多语言叠加是否按 `#lang=` 正确显示（D-016）。
- 稳定后可加入小容差的像素对比。
- E2E 同时做 DOM/JS 断言（`window.__app.ready`、`zoom`、`visibleLabelCount`），避免只依赖截图。

### 13.3 质量门禁

以下任一失败禁止标记任务完成：

- `uv run mapcreator check --full --json` 非零退出。
- 数据校验存在错误（警告需记录）。
- UI 变更无截图证据。
- 新依赖未登记。
- schema/DB 变更无迁移或文档。
- 构建不可重复（golden 变化未解释）。
- 性能超出预算且无 ADR。

### 13.4 CI（可选）

- 本地 `check --full` 是硬要求；GitHub Actions 可选。
- CI 不跑需要 QGIS/Docker 的可选步骤；用 `doctor` 标记跳过。
- 截图 artifacts 在 CI 中上传，供评审。

---

## 14. 性能预算

目标硬件：现代笔记本，集成显卡，最新 Edge/Chrome。

| 指标 | 预算 | 触发动作 |
|---|---|---|
| 源要素 | ≤ 50k 几何 + ≤ 20k 标注 | 超出则先拆分图层/区域 |
| 全量构建 | ≤ 20 s | 超出则分析瓶颈 |
| 增量构建 | ≤ 3 s | 超出则优化合并/样式 |
| 初始数据载荷（gzip） | ≤ 8 MB | 超出则按缩放带拆分 |
| 每缩放带标注 | ≤ 3000 | 超出则裁剪低 rank |
| 页面可交互 | ≤ 2.5 s（本地） | 超出则预加载/拆分 |
| 缩放/平移 | ≥ 55 fps 典型场景 | 超出则简化/拆分 |
| 搜索 p95 | ≤ 100 ms | 超出则检查索引/查询 |
| 浏览器内存 | ≤ 300 MB | 超出则拆分/卸载 source |
| 只读静态包 | ≤ 50 MB（不含可选地形；M5 之后生效） | 超出则子集化字体/图标 |

性能测量写入 `artifacts/perf.json`；`check --full` 对比基线，回归 >10% 需 ADR。

---

## 15. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 编辑器范围失控 | 项目延期 | MVP 只做点/线/面/属性；拓扑交给 QGIS；复用 Terra Draw |
| 标注碰撞/视觉质量调参耗时 | 体验差 | 配置驱动 + 截图迭代；MapLibre 原生碰撞；限制每带数量 |
| Windows 工具链缺失（tippecanoe/native glyph/sprite） | 构建受阻 | MVP 不用瓦片；预生成字体/图标；后续 Docker/WSL 或 ADR 自研 |
| 中文字体缺字 | 标注乱码 | `localIdeographFontFamily` + 系统字体；Noto Sans PBF 只覆盖拉丁 |
| 几何/标注双真源不一致 | 数据错误 | 单一写路径、ID 契约、构建强校验、统一只读视图 |
| AI 编造 API/依赖 | 返工 | 锁定版本、示例、冒烟测试、`DEPENDENCIES.md` |
| 无头 WebGL 截图不稳定 | 误判 | 先做 JS 断言 + 截图人工/AI 检查；后期再加像素容差 |
| 虚构世界投影/比例尺不准确 | 认知偏差 | 限定纬度范围；文档说明；自定义比例尺 |
| 数据库无版本管理 | 数据丢失/难回滚 | 提交 SQL dump；`verify-dump`；备份命令 |
| 性能预算被突破 | 卡顿 | 先分级分片/简化；再考虑瓦片；有测量数据再决策 |
| 许可证污染 | 分发风险 | 依赖审计；QGIS 仅外部工具；记录字体/图标许可 |
| AI 上下文过载 | 决策质量下降 | 核心文档 ≤ 600 行；单一入口；STATUS/DECISIONS |
| 过度设计 | 迟迟不能演示 | M0/M1 先跑通；非目标明确；任务小步 |
| Windows 路径/编码问题 | 构建失败 | pathlib、UTF-8、无 shell 拼接、`doctor` 检查 |

---

## 16. 许可证与合规

- 所有依赖引入时登记到 `docs/DEPENDENCIES.md`，包含许可证与分发影响。
- 预计主要许可证：
  - MapLibre GL JS：BSD-3-Clause
  - Terra Draw：MIT
  - FastAPI：MIT；Uvicorn：BSD-3
  - Pydantic：MIT；Shapely：BSD-3
  - SQLite：Public Domain
  - Vite：MIT；Node.js：MIT
  - Playwright：Apache-2.0
  - QGIS：GPL（**仅作为外部工具使用，不链接、不捆绑进分发物**）
  - Noto Sans：OFL；图标集：以实际仓库 LICENSE 为准
- 字体/图标附 `assets/ATTRIBUTION.md`。
- 若未来分发打包，重新审计 GPL/AGPL 依赖；不要因为“本地使用”而忽略。
- 地图数据版权归项目作者；如引入第三方世界数据，记录来源与许可。

---

## 17. 端到端应用流程

### 17.1 首次初始化

```bash
# 前置：安装 Python 3.12+、uv、Node 20+、现代浏览器
uv sync
uv run mapcreator setup
uv run mapcreator doctor --json
uv run mapcreator build
uv run mapcreator serve
```

打开 `http://127.0.0.1:8765`。

### 17.2 日常浏览

1. 启动 `uv run mapcreator serve --dev`。
2. 浏览器缩放/平移；前端按缩放带加载数据。
3. 搜索城市/医院/车站；点击结果定位并高亮。
4. 点击要素查看详情、属性、描述。
5. URL 可复制分享当前视图与选中要素。

### 17.3 日常编辑（Web）

1. 启动时加 `--enable-edit`。
2. 进入编辑模式，选择点/线/面工具。
3. 绘制后填写属性表单（名称、kind、rank、缩放、描述、业务属性）。
4. 保存 → 服务端校验 → 写入 → 增量构建 → 页面刷新。
5. 拖动标注锚点优化位置；软删除要素可恢复。

### 17.4 批量/拓扑编辑（QGIS，可选）

```bash
uv run mapcreator export --qgis
# 在 QGIS 中编辑 build/qgis/ 下的图层
uv run mapcreator geometry import --dir build/qgis/geometry
uv run mapcreator annotations import --geojson build/qgis/annotations.geojson
uv run mapcreator format
uv run mapcreator build
```

### 17.5 数据备份与恢复

```bash
uv run mapcreator backup --out backups/
uv run mapcreator db dump --out world/annotations.sql
uv run mapcreator db verify-dump --in world/annotations.sql
uv run mapcreator db restore --in world/annotations.sql
```

### 17.6 发布只读版本

```bash
uv run mapcreator build --clean
uv run mapcreator export --static --out dist/
# 用任意静态 HTTP 服务打开 dist/
```

> **MVP 不交付静态站点**：整个 17.6 推迟到 M5 之后（D-019）。届时需先确认静态搜索的实现方式（见 §18.2）。

---

## 18. 待确认问题与复核结论

> **状态**：2026-11-03 已与人类逐条复核。18.1 为**已确认**（可直接实现）；18.2 为**仍未确认**（实现时不得假设，相关任务需置 blocked 或降级）；18.3 为文档自身的缺口，已给出处置。

### 18.1 已确认（2026-11-03）

| # | 原问题 | 结论 | 落点 |
|---|---|---|---|
| 1 | 世界范围 / 是否完整星球 | **小范围有界区域，二维俯视**；不处理纬度限制与投影变形；`bounds` 由构建从数据自动推导，`world.toml` 可覆盖；`max_zoom = 17` | D-013、§5.1 |
| 2 | 数据规模 | 沿用 §2.2：≤ 5 万几何要素 + ≤ 2 万标注；最小验收样例为 mini-world | §2.2、§11 |
| 3 | 语言 | **标注名称多语言**（同一地标可中英并存、可叠加显示）；**界面中文为主**，文案 key 化、保留多语言空间，不引入 i18n 框架 | D-016、D-020、§5.4.1、§7.4 |
| 4 | QGIS | **可选外部工具，不装也能跑**；拓扑编辑的兜底是 Web 基础校验 + 构建期有效性检查，强拓扑延后 | D-007、§8.1 |
| 5 | 分发形式 | **源码运行 + 本地 `serve`**；打包 exe 不做；静态导出整体后移到 M5 之后 | D-019、§18.2 |
| 6 | 地形表现 | 平面色块 + 高程分级，不做 DEM/hillshade（M5 后可议） | §7.3 |
| 7 | 交通 | 只展示线路与站点，不做路径规划/ETA（沿用非目标） | §2.4 |
| 8 | 局域网/远程 | **仅本机 `127.0.0.1`**，不开放局域网 | §9.4 |
| 9 | 图标风格 | Maki/Temaki 风格的线性图标，许可证随依赖登记 | §6.4、§16 |
| 10 | 标注真源 | **接受双真源**：几何在 GeoJSON、标注/名称/属性在 SQLite；点标注不建几何 | D-004、D-015 |
| 11 | 标注 ID 格式（新增） | **`anno.<kind>.<slug>`**，与 `geo.<kind>.<slug>` 对称；URL `sel=` 用它 | D-014、§5.4.1、§7.4 |
| 12 | 中文短词搜索（新增） | trigram 覆盖 ≥3 字符，**<3 字符回退 LIKE 扫描** | D-017、§5.4.2 |
| 13 | 缩放带权威（新增） | 带边界**只**由 `zoom_bands.toml` 定义（6 个固定带），kind 的 zoom 只做带内过滤 | D-018、§6.2、§7.1 |
| 14 | 跨模块数据传递（新增） | **只传 ID**，详情按 ID 回查 DB；渲染分片由构建期从 DB 生成（含名称） | D-016、§8.6 |

### 18.2 仍未确认（实现时不得假设）

| # | 问题 | 当前临时处置 | 阻塞的任务 |
|---|---|---|---|
| 1 | **静态导出**的范围与验收（是否含搜索、目标包体） | 整体后移到 M5 之后；MVP 不做静态导出 | TASK-0009 / M5 |
| 2 | 真实世界内容（地名、图层密度、首批地区） | 先用 mini-world + 占位世界跑通管线 | M1 之后 |
| 3 | 图标集最终选型与视觉规格（线宽、圆角、色彩） | 先用 Maki 风格占位，允许 M3 前更换 | 无阻塞 |
| 4 | 编辑模式是否需要**撤销历史持久化**（跨会话） | 先只做会话内撤销（Terra Draw 自带） | M3 |
| 5 | 是否需要**多世界**（一次切换多个 `world/`） | 假定单世界，配置保留 `world.id` 字段 | 无阻塞 |

### 18.3 本轮发现并已处置的文档缺口

| 缺口 | 处置 |
|---|---|
| `world.max_zoom=15` 与 `kinds.hospital.default_max_zoom=17` 冲突 | `max_zoom` 统一为 17，并新增 `z16-17` 带（§5.1、§6.2） |
| 标注 ID 前缀三种写法（`poi.` / `city.xxx` / 无前缀） | 统一 `anno.<kind>.<slug>` + DB `CHECK`（§5.4.1、D-014） |
| 点标注是否存 GeoJSON Point | 不存；点坐标只在 `annotation.lon/lat`（D-015） |
| 名称三语种方案（`name`/`name_en`/`aliases`） | 改为 `annotation_name` 子表 + 唯一主名 + `annotation_v` 视图（§5.4.1、D-016） |
| trigram 无法命中 <3 字符 | LIKE 回退 + 边界测试用例（§5.4.2、§13.1、D-017） |
| `world/manifest.json` 与 `build/manifest.json` 同名不同物 | 输入侧改名 `world/world.json`（§5.2、§11） |
| API 只有一个端点在正文出现 | 新增 §8.6 端点清单与载荷约定 |
| GeoJSON `properties` 无白名单（连 `layer` 都冗余） | 删除 `layer`，新增逐层属性白名单表（§5.3） |
| kind 注册表只有 3 个示例 | 新增 27 个 kind 的首批注册表（§7.6） |
| 缩放带内容只写在正文、无配置文件示例 | 新增 `zoom_bands.toml` 完整示例 + 简化容差初值（§6.2） |
| 字号/图标尺寸无任何数值 | 新增 rank × zoom 字号初始表（§7.1） |
| 删除几何时关联标注的处理未定义 | 409 + `--cascade`（§8.2、§8.6） |
| `annotations.sql` 是否含 FTS/RTree 影子表未定义 | 只导逻辑表，restore 重建索引（§5.5） |
| `relation_member.member_id` 指向类型未定义 | 注释明确 stop/platform→annotation、section→geo 要素（§5.4.1） |
| 缺少“点标注带 geometry_id”“线标注关联面”等校验 | 写入 §5.7 错误清单 |

---

## 19. 决策记录（ADR 摘要）

| ID | 决策 | 状态 | 理由 | 备选 |
|---|---|---|---|---|
| D-001 | 本地优先 Web 应用（FastAPI + 浏览器） | 已定 | 跨平台、易截图/测试、复用 WebGL 生态 | 纯桌面 PySide6 |
| D-002 | MapLibre GL JS 作为渲染引擎 | 已定 | WebGL、标注碰撞、LOD 成熟 | Leaflet、OpenLayers、deck.gl |
| D-003 | Python 主导，JS 仅前端壳 | 已定 | 满足主语言偏好；构建/校验/服务 Python | 全 JS/TS |
| D-004 | 几何用 GeoJSON，标注用 SQLite | 已定 | 职责清晰；AI 可读 + SQL 可查 | 全 GeoJSON；全 GeoPackage |
| D-005 | RFC 7946 经纬度作为坐标格式 | 已定 | 工具兼容性最好 | 自定义平面 CRS |
| D-006 | MVP 不引入瓦片，使用缩放带 GeoJSON 分片 | 已定 | 小地图足够；避开 Windows 切片工具链 | MBTiles/PMTiles |
| D-007 | Terra Draw 做 Web 编辑，QGIS 做批量/拓扑 | 已定 | 复用成熟项目，避免自研编辑器 | MapLibre Draw；纯自研 |
| D-008 | 前端原生 JS + JSDoc，不用框架 | 已定 | 轻量、AI 可读、满足“非 TS 主语言” | React/Vue/TS |
| D-009 | 字体用 Noto Sans PBF + 本地 CJK 字体 | 已定 | 避开 Windows glyph 生成难题 | 自建 glyph 服务 |
| D-010 | 标注工作库 + 提交 SQL dump | 建议 | 兼顾 SQL 管理与 Git/AI 可读 | 二进制 DB 提交；纯 JSON |
| D-011 | AI 一切操作走 `mapcreator` CLI/JSON | 已定 | 可执行、可验证、可复现 | 手工 MCP/GUI |
| D-012 | 自研组件必须 ADR | 已定 | 防止重复造轮子 | 自由引入依赖 |
| D-013 | 世界=小范围**有界区域 + 二维俯视**；不处理纬度/投影变形；`bounds` 由构建自动推导（可覆盖）；`max_zoom = 17` | 已定 | 与“虚构小地图”定位一致，避开投影与比例尺失真问题 | 完整星球；手填固定 bounds |
| D-014 | 标注 ID 固定 `anno.<kind>.<slug>`，DB 加 `CHECK`；URL/API 一律用它 | 已定 | 与 `geo.*` 对称，一眼可辨类型，避免三处写法并存 | `poi.*`；无前缀 `<kind>.<slug>` |
| D-015 | **点标注不建 GeoJSON 几何**，坐标只在 `annotation.lon/lat`；线/面标注关联 `geometry_id` | 已定 | 单一真源，避免点位双写漂移；编辑器实现更直接 | 每个点也生成 Point 要素 |
| D-016 | 名称/别名/描述只存 SQLite；名称拆 `annotation_name` 子表（多语言 + 唯一主名）；构建期由 DB 生成含名称的渲染分片 | 已定 | 支持“中英文同时显示”，可按语种索引；渲染分片是派生物，可重建 | `names` JSON 列；`name`/`name_en` 两列 |
| D-017 | 搜索：≥3 字符走 FTS5 trigram，**<3 字符回退 LIKE** | 已定 | 中文双字词（最常见）可用，零新增依赖 | jieba 分词；只支持 ≥3 字符 |
| D-018 | 缩放带边界**只**由 `config/zoom_bands.toml` 定义（6 个固定带）；kind 的 zoom 仅做带内 style filter | 已定 | 构建确定性、golden 稳定；改 kind 不重排文件名 | 由 kind 反推带边界；不分带 |
| D-019 | **静态导出推迟到 M5 之后**，MVP 验收不含静态站点 | 已定 | 先保住浏览+搜索+编辑闭环，避免过早分叉两条数据通道 | MVP 内实现静态导出 |
| D-020 | 界面中文为主、文案 key 化、不引 i18n 框架；标注名称多语言见 D-016 | 已定 | 轻量、AI 可读；保留多语言扩展空间 | 中英双语框架；中文硬编码 |
| D-021 | 跨模块与 API 载荷以 **ID** 为准，详情按 ID 回查；仅搜索/详情接口返回名称 | 已定 | 载荷小、单一真源；避免宽表广播导致的不一致 | 宽表广播 |

---

## 20. 术语表

| 术语 | 含义 |
|---|---|
| 真源（SoT） | 唯一权威数据来源；其他为派生/缓存 |
| LOD | Level of Detail，按缩放级别决定显示内容 |
| Collision | 标注碰撞检测与避让 |
| Symbol | MapLibre 的文字/图标图层要素 |
| Glyph / PBF | 字体字形文件；MapLibre 文字渲染所需 |
| Sprite | 图标图集；MapLibre 图标渲染可选方案 |
| GeoJSON | RFC 7946 地理要素 JSON 格式 |
| Web Mercator | MapLibre 使用的 EPSG:3857 投影 |
| FTS5 | SQLite 全文搜索扩展；本项目用 trigram |
| R\*Tree | SQLite 空间索引扩展 |
| Terra Draw | 开源 Web 地图绘制库 |
| Maputnik | 开源 MapLibre 样式编辑器 |
| ADR | Architecture Decision Record，架构决策记录 |
| DoD | Definition of Done，完成定义 |
| Golden Test | 对规范化输出做快照/比对测试 |

---

## 附录 A：给其他 AI 的评审提示词

```text
你是资深 GIS / 本地 Web 地图应用架构师。请审阅 MapCreator 开发准备文档。

重点检查：
1. 技术选型在 Windows 11 本地环境的可行性（原生依赖、字体、切片、浏览器 WebGL）；
2. 是否存在重复造轮子，是否有更成熟的开源替代；
3. 数据模型（GeoJSON 几何 + SQLite 标注）的一致性、可迁移性与 AI 可读性漏洞；
4. 缩放分级标注方案是否会在真实数据量下失效；
5. AI Agent 开发协议是否足以防止幻觉、回归与不可验证的“完成”；
6. 被低估的风险、缺失的验收标准、过度设计。

输出要求：
- 按严重级别（Blocker / High / Medium / Low）列问题；
- 每条注明文档章节与理由；
- 给出具体、可执行的修改建议；
- 不要泛泛而谈，不要重复文档已有内容。
```

---

**文档结束。** 0.2 版已确认技术方向（§18.1），下一步直接执行 TASK-0001（仓库骨架与 AI 入口）；M0 结束时把本文档拆分为 `AGENTS.md` 与 `docs/*.md`，并在 `docs/DECISIONS.md` 中登记 D-001–D-021。
