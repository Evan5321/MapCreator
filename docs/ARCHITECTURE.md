# 架构（ARCHITECTURE）

> 目标 ≤ 200 行。数据字段与校验规则见 [`DATA_SPEC.md`](DATA_SPEC.md)；决策理由见 [`DECISIONS.md`](DECISIONS.md)。
> 版本：随 v0.2 契约建立。

## 1. 系统边界

一个**单机、单用户、单进程**的本地 Web 应用：浏览器负责渲染与交互，Python 负责数据、校验、构建与服务。

```text
┌──────────────────────────────────────────────────────┐
│ Web Client（原生 JS + MapLibre + Terra Draw）         │
└───────────────────────────┬──────────────────────────┘
                            │ HTTP / JSON / GeoJSON
┌───────────────────────────▼──────────────────────────┐
│ FastAPI（127.0.0.1:8765，单 worker，单进程）            │
│ 静态资源 / 数据 API / 编辑 API / 只读 SQL              │
└───────────────────────────┬──────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────┐
│ Build Pipeline（Python，纯本地计算）                   │
│ 校验 → 合并 → 样式 → 分带 → manifest → 原子发布        │
└───────────┬───────────────────────────────┬──────────┘
            │                               │
┌───────────▼─────────────┐     ┌───────────▼──────────┐
│ 真源                     │     │ 可选外部编辑器        │
│ world/world.json         │     │ QGIS（GPL，外部）     │
│ world/geometry/*.geojson │     │ 通过 file 往返        │
│ world/annotations.db     │     │                       │
└─────────────────────────┘     └──────────────────────┘
```

**不负责**：多用户、权限、远程访问、真实地理精度、路径规划、在线瓦片服务。

## 2. 进程与端口

| 进程 | 说明 |
|---|---|
| `uv run mapcreator serve` | 唯一本地服务，默认 `127.0.0.1:8765`，单 Uvicorn worker。**禁止默认绑定 `0.0.0.0`。** |
| `uv run mapcreator build` | 一次性进程，写 `build/`，结束即退出 |
| `uv run mapcreator serve --dev` | 叠加 watchfiles 监听 `world/`、`config/`、`web/src/`，重建并提示刷新 |
| Vite dev server | **可选**，仅在改前端时需要；产物最终由 FastAPI 提供 |

## 3. 模块与职责

| 模块 | 职责 | 不负责 |
|---|---|---|
| `src/mapcreator/cli.py` | Typer 入口、退出码、`--json` 输出 | 业务逻辑 |
| `src/mapcreator/config.py` | 读取/校验 `config/*.toml`（Pydantic Settings） | 修改配置 |
| `src/mapcreator/models.py` | Pydantic 模型：GeoJSON 要素、标注、kind、带 | 存储 |
| `src/mapcreator/errors.py` | 统一异常（`code/path/feature_id/remediation`） | 记日志 |
| `db/repo.py` | **唯一** SQLite 访问层：CRUD、事务、FTS/RTree/触发器维护 | 业务规则 |
| `data/geometry.py` | GeoJSON 读取、格式化、Shapely 校验/修复 | 标注 |
| `data/annotations.py` | 标注 + 名称的校验与归一化 | 几何 |
| `build/pipeline.py` | 编排 11 步构建、原子发布 | 渲染 |
| `build/style.py` | base/generated/overrides 合成 + style-spec 校验 | 手工设计 |
| `build/bands.py` | 按带切分、简化、可见性判定 | 样式颜色 |
| `build/assets.py` | 图标栅格化、字体 glyph 准备、哈希 | 版权登记 |
| `build/manifest.py` | 输入哈希、计数、构建版本 | 时间戳（**禁止**） |
| `server/app.py` | FastAPI 应用装配、模式开关 | 校验规则 |
| `server/routes.py` | API 端点（见 §6） | 直接读写文件 |
| `server/static.py` | 静态资源、SPA 回退、缓存头 | 构建 |
| `qgis/roundtrip.py` | 导出/导入 GeoJSON 往返 | 拓扑检查 |
| `web/src/map.js` | MapLibre 实例、source/layer、缩放带切换 | 业务数据 |
| `web/src/shell.js` | 浏览/编辑共用外壳、左栏与顶栏、模式切换 | 绘制逻辑 |
| `web/src/panels.js` | 面板零件（分节、行、开关、滑杆、属性卡） | 数据请求 |
| `web/src/layers.js` | 图层分组、开关、图例 | 样式生成 |
| `web/src/pick.js` | 点选容差、最近命中、顶点手柄 | 渲染 |
| `web/src/shortcuts.js` | 快捷键表与匹配 | 业务动作 |
| `web/src/history.js` | 会话内撤销/重做快照栈 | 持久化 |
| `web/src/editor.js` | Terra Draw 工具模式、绘制/拖拽、保存提交 | 持久化 |
| `web/src/api.js` | 请求封装、错误归一化 | 校验唯一防线 |

浏览模式只挂载 `map/shell/panels/layers`，编辑工具（`editor/pick/history` 的 UI 部分）仅在编辑模式加载。

## 4. 三条数据流

**浏览**：`world/` → `build` → `build/data/labels.<band>.geojson` 等 → FastAPI 静态提供 → MapLibre 渲染。

**编辑**：浏览器/QGIS → 统一写入口（FastAPI `--enable-edit` 或 CLI）→ Pydantic + Shapely + 引用检查 + `revision` 检查 → 写 GeoJSON / SQLite 事务 → 增量构建 → 页面刷新。

**编辑（TASK-0009 临时库）**：浏览器编辑器 → dev-only 写端点（`serve --editable`）→ 同样的校验链 → `var/editor-test/annotations.db` + `var/editor-test/geometry/` → 用临时库预览构建。该路径永不打开 `world/annotations.db`。

**AI 查询**：`mapcreator describe/query/export --json` → 结构化 JSON；AI 永不直接解析二进制 DB。

## 5. 构建管线（11 步）

1. 读 `config/*.toml` 与 `world/world.json`。
2. 解析 GeoJSON（`geojson-pydantic`）。
3. Shapely 校验（`--fix` 才 `make_valid`），坐标格式化到 6 位小数。
4. 读 `annotations.db`，校验引用、唯一性、`search_text` 一致性。
5. 合并：`annotation.geometry_id ↔ feature.id` → 统一要素。
6. 推导 `min_zoom/max_zoom`（kind 默认值 + 标注覆盖；**不回写库**）。
7. 生成样式：`styles/base.maplibre.json` → generated → `overrides` → style-spec 校验。
8. 按带切分：labels / lines / polygons per band（带边界来自 `zoom_bands.toml`）。
9. 准备资产：图标、glyph、调色板。
10. 写 `build/` + `manifest.json`（输入哈希、计数、`build_version`、推导出的 `bounds`）。
11. 原子发布：`.tmp-build/` → 替换 `build/`；失败保留上一次产物。

**确定性**：稳定排序（图层名 → ID → 主键）、固定缩进、无时间戳、字体/图标记录哈希。同输入同版本必须字节级一致。

## 6. HTTP API 契约（M0 冻结）

| 方法 | 路径 | 用途 | 模式 |
|---|---|---|---|
| GET | `/api/health` | 存活、版本、`build_id` | 只读 |
| GET | `/api/world` | 世界元数据、kind 注册表、缩放带、bounds | 只读 |
| GET | `/api/data/{band}` | 渲染分片 | 只读 |
| GET | `/api/annotations/{id}` | 详情（多语言名称、attrs、geometry_id） | 只读 |
| GET | `/api/search?q=&lang=&limit=` | FTS + 短词回退 | 只读 |
| GET | `/api/map/{bbox}?zoom=` | RTree 视口查询，返回 ID 列表 | 只读 |
| POST | `/api/query` | 只读 SQL（`--enable-sql`） | 只读 |
| POST/PATCH/DELETE | `/api/annotations[/{id}]` | 标注增改与软删/恢复 | 编辑 |
| POST/DELETE | `/api/geometry[/{id}]` | 线/面几何增改与删除（被引用 → 409） | 编辑 |
| POST | `/api/build` | 增量构建（`--dev`） | 编辑 |

约定：写接口必须带 `revision`（409 `REVISION_CONFLICT`）；除搜索/详情外**载荷只给 ID 与渲染必需字段**；错误体统一 `code/message/path/feature_id/details/remediation`；编辑端点未开启时返回 404。

开发模式（TASK-0009）：`serve --editable --editor-db var/editor-test/annotations.db` 时，`/api/annotations` 的写方法与详情读取指向临时库，几何写 `var/editor-test/geometry/`；路径解析后校验不得等于 `world/annotations.db`。普通 `serve` 不注册写端点。

## 7. 渲染与分带

- 6 个固定带（`z0-3 … z16-17`），带边界**只**由 `config/zoom_bands.toml` 定义。
- 标签分片按带加载/卸载（`/api/data/{band}`）；几何当前合并为 `unified.geojson`，按带裁剪见 TASK-0012。
- 标签当前为 DOM 层 + 屏幕空间贪心碰撞（ADR-021）；可见点超过约 1 万时切 symbol layer + 自托管 glyph。
- 碰撞由 `rank` 排序与先到先得决定；每带可见标注 ≤ 3000，超出裁剪低 rank。

## 8. 存储布局

| 路径 | 性质 | 提交 |
|---|---|---|
| `world/geometry/*.geojson` | 几何真源 | 是 |
| `world/annotations.db` | 标注工作库（WAL） | 否 |
| `world/annotations.sql` | 逻辑表 dump | 是 |
| `world/world.json` | 世界元数据、图层清单、schema 版本 | 是 |
| `build/` | 产物（含 `manifest.json`） | 否 |
| `artifacts/` | 截图与性能报告 | 否 |
| `logs/app.jsonl` | 运行日志 | 否 |
| `var/editor-test/` | 编辑器临时库与几何（TASK-0009） | 否 |

## 9. 复用优先（"不要重复造轮子"）

| 需求 | 复用 | 理由 |
|---|---|---|
| 渲染/缩放/碰撞 | MapLibre GL JS | WebGL + LOD 极复杂 |
| 点线面绘制/顶点编辑 | Terra Draw | 交互状态机复杂 |
| 样式调参 | Maputnik | 现成编辑器官 |
| 批量/拓扑 | QGIS | 成熟桌面 GIS |
| GeoJSON 模型 | geojson-pydantic | 标准字段易漏 |
| 几何运算 | Shapely | 计算几何不手写 |
| 搜索/空间索引 | SQLite FTS5 + R*Tree | 内建零部署 |
| 属性表单 | JSON Editor | Schema 驱动 |
| 字体 glyph | OpenMapTiles fonts | 避开 Windows 字体工具链 |
| E2E/截图 | Playwright | 驱动与截图成熟 |

找不到现成方案时：先写 ADR（候选、不采用原因），再自研。

## 10. 安全边界

- 默认只读；编辑需 `--enable-edit`，SQL 需 `--enable-sql`。
- 校验 `Origin`/`Host` 防本地 CSRF；可选启动 token。
- SQL 接口只允许 `SELECT`/`WITH`，只读连接、超时、行数上限。
- 文件写入 `临时文件 + os.replace`；构建用目录原子替换。
- 数据目录与代码目录分离，服务不以写权限访问 `src/`。
- `--editor-db` 解析为绝对路径后必须拒绝 `world/annotations.db` 与 `world/geometry/`；临时库只允许落在 `var/`。

## 11. 失败模式（必须显式处理）

| 情况 | 行为 |
|---|---|
| GeoJSON 无效且未 `--fix` | 中止构建，报 `path` + `feature_id` |
| dump 与工作库不一致 | 构建前中止，提示先 `db dump` |
| 编辑冲突（`revision` 旧） | 409，不覆盖 |
| 删除被引用几何 | 409 + 引用列表；`--cascade` 才级联 |
| 端口占用 | 退出码 3，提示换端口 |
| 构建中断 | `build/` 保持上一次产物 |
| 字体/图标缺失 | 构建失败并列出缺失项（不静默回退） |

## 12. 扩展点（不在 MVP）

- 瓦片（PMTiles/tippecanoe）：仅在性能预算被突破时启用。
- 多世界切换：当前假定单 `world/`。
- 静态导出：推迟到 M5 之后（D-019）。
- 多用户/远程：当前明确不做。
