# 项目状态（STATUS）

- **当前分支**：`feat/civ-atlas-ui` 只做 **UI 界面**（浏览界面 + 编辑界面）；不写 TASK-0008 搜索/只读 SQL，也不写任何后端写端点
- **当前里程碑**：M1 完成（TASK-0003 ~ TASK-0007），TASK-0013 浏览外壳与 TASK-0009 阶段 A（纯前端编辑器）已完成；下一步 TASK-0008（另分支），编辑落库阶段 B/C 留后续分支
- **最近更新**：2026-11-23
- **维护规则**：每完成一个任务更新本文件；只写事实与证据，不写计划口号（计划在 `TODO.md`）。

## 已完成

- 开发契约 `DEVELOPMENT_PREP.md` 定稿 v0.2（§18 十问确认，D-013–D-021 入档）。
- 文档拆分：`AGENTS.md`、`CLAUDE.md`、`README.md`、`TODO.md`、`docs/*.md`（8 份）。
- **仓库骨架（TASK-0001 文件部分）**：
  - 根配置：`pyproject.toml`、`package.json`、`biome.json`、`.gitignore`、`.gitattributes`、`.editorconfig`、`git init`。
  - `config/`：world / kinds（27 个 kind）/ zoom_bands（6 带）/ palette。
  - `schemas/`：geometry、annotation、annotation-name、style-input + 10 个 kind 属性 schema。
  - `world/`：`world.json`、7 个空 `FeatureCollection`、README。
  - `src/mapcreator/`：CLI、config、models、errors、doctor、db/schema.sql、db/repo、data、build、server、qgis 占位模块。
  - `web/`：index.html、7 个 ES 模块、style.css、i18n/zh.json、vite.config.js。
  - `tests/`：conftest、unit/integration/e2e 占位、golden 与 mini-world 目录。
  - `styles/`、`assets/ATTRIBUTION.md`、`tasks/README.md`、`.github/workflows/check.yml`。
  - `scripts/install-deps.ps1` + `install-deps.sh`。
- **依赖本地化（2026-11-18，TASK-0001 收尾）**：
  - Python：`.venv`（CPython 3.13.14）+ `uv.lock`（46 个包）；镜像走清华 TUNA（`pyproject.toml` 的 `[tool.uv.index]`）。
  - 前端：`node_modules`（55 包）+ `package-lock.json`；`npm ci` 可复现；镜像走 `npmmirror`（`.npmrc`）。
  - 工具链实测：uv 0.11.32 / Node v24.16.0 / npm 11.13.0 / Git 2.54.0 / SQLite 3.50.4（FTS5+RTree+trigram 可用）。
  - Playwright Chromium 已安装到 `C:\Users\liyunlin\AppData\Local\ms-playwright`（`chromium-1255` + `chromium_headless_shell-1255`），`doctor` 检测为 ok。
- **TASK-0002 `doctor`**：
  - [doctor.py](../src/mapcreator/doctor.py) 只读探测 Python/uv/Node/npm/git/SQLite 能力/Playwright/可选工具。
  - `--json` 输出 `checks[]`（含 `status`/`required`/`remediation`）；必需项缺失退出码 3。
  - [test_doctor.py](../tests/unit/test_doctor.py) 用注入的 `which`/`run` 模拟缺失与低版本。
- **构建链路修复（依赖安装时暴露）**：
  - `web/vite.config.js` 以配置文件目录为 root，`package.json` 脚本显式 `--config web/vite.config.js`；`npm run build` 产出 `web/dist/index.html`。
  - `biome.json` 启用 `vcs.useIgnoreFile` 并忽略 `world/`、`node_modules/`、`dist/`；`npm run check` 通过。
  - `pyproject.toml` 关闭 Ruff 的 RUF001/002/003（中文标点误报），为 Typer 关闭 B008。

- **TASK-0003 配置与 schema（2026-11-19）**：
  - 4 个 TOML 全部走 Pydantic：`config.py`（world/kinds/zoom_bands + 交叉校验）、`palette.py`（`PaletteConfig`、`label_tokens`、HexColor）、`models.py`（`WorldDocument`/`LayerDef`）。
  - 非法值报错含字段路径：[errors.py](../src/mapcreator/errors.py) 的 `config_error_from` / `data_error_from`（`code: CONFIG_INVALID` / `SCHEMA_INVALID`）。
  - `mapcreator schema --out schemas` 由模型导出 JSON Schema，[test_schema_export.py](../tests/unit/test_schema_export.py) 守确定性（`sort_keys` + 固定缩进 + LF）。
  - 几何/标注加载：[data/geometry.py](../src/mapcreator/data/geometry.py)（kind、几何类型、属性白名单、重复 ID）、[data/annotations.py](../src/mapcreator/data/annotations.py)、[data/world.py](../src/mapcreator/data/world.py)（bounds 推导 + `describe_world`）。
  - mini-world 夹具：7 层几何、6 个要素、8 条标注；`describe --json` bounds=`[9.95, 6.95, 14.55, 11.05]`。
- **TASK-0004 数据库层（2026-11-19，已验收）**：
  - [db/core.py](../src/mapcreator/db/core.py)（`SCHEMA_VERSION=1`、`connect`、`init_schema`）、[db/store.py](../src/mapcreator/db/store.py)（CRUD、主名唯一、revision 乐观锁、FTS/LIKE 搜索、软删除）、[db/dump.py](../src/mapcreator/db/dump.py)（逻辑表 dump/restore/rebuild_indexes/verify_dump/check_search_text）、[db/repo.py](../src/mapcreator/db/repo.py)（仅重导出，保持唯一入口）。
  - CLI：[cli_db.py](../src/mapcreator/cli_db.py) 的 `db init|dump|restore|verify-dump|migrate` 与 `annotations export|import`。
  - 单测：[test_db.py](../tests/unit/test_db.py) 覆盖主名唯一、revision、2 字 LIKE、3 字 FTS、别名、软删除、触发器、dump→restore 字节一致、search_text 漂移检出、CLI 往返。
  - **真实路径（2026-11-19，人类终端）**：`db init` → `annotations import`（`count: 8`）→ `db dump` → `db restore` → `db verify-dump`（`checked: logical-tables`）全部退出码 0；`annotations.db` 114688 B、`annotations.sql` 5489 B、`schema_version: 1`、无残留 journal。
- **TASK-0005 构建合并（2026-11-19）**：
  - [build/pipeline.py](../src/mapcreator/build/pipeline.py)：校验 → 合并 → 分带 → 写 `.tmp-build/` → 原子替换 `build/`；失败保留上次产物并清理临时目录。
  - [build/bands.py](../src/mapcreator/build/bands.py)：带只取自 `zoom_bands.toml`；kind 默认 zoom 回填；`label_mode=none` 不进标签；单带上限 3000（按 `rank, id` 裁剪）；`simplify_geometry` 用 shapely + 6 位小数。
  - [build/manifest.py](../src/mapcreator/build/manifest.py)：`input_hash`（路径 + 内容，排序后总哈希）、稳定键序 JSON、读写校验。
  - 产物：`build/unified.geojson`（几何 + 标注点）、`build/annotations.export.json`、`build/data/labels.<band>.geojson`（6 个）、`build/manifest.json`（`build_version` + 计数 + 文件 sha256，**无时间戳**）。
  - CLI：`validate --root ... --json` 只读；`build --json` 输出产物清单。
  - 数据读取：[data/annotations.py](../src/mapcreator/data/annotations.py) 优先 `annotations.json`，否则经 `db/repo.py` 读工作库。
  - 几何：`data/geometry.py` 实现 `normalize`（6 位小数、去 -0.0）与 `validate_geometry`（shapely 有效性）。
  - 测试：`tests/unit/test_build.py`、`tests/integration/test_build_mini_world.py`（含两次构建字节一致、失败保留旧产物）。
- **TASK-0006 样式与前端地图（2026-11-19）**：
  - [build/style.py](../src/mapcreator/build/style.py)：读取 `styles/base.maplibre.json`，生成 `build/style.json`（source=`unified.geojson`；land/water/parks/terrain/river/road/transit 图层；每 kind 一个 circle 层，`minzoom/maxzoom` 取自 `kinds.toml`，无 glyph）。
  - [server/routes.py](../src/mapcreator/server/routes.py)：`/api/health`、`/api/world`（bounds/bands/kinds/typography）、`/api/data/{band}`；manifest 缺失返回 503 与修复建议。
  - [server/static.py](../src/mapcreator/server/static.py)、[server/app.py](../src/mapcreator/server/app.py)：`web/dist` 挂 `/`，`build/` 挂 `/map`；`web/dist` 缺失时抛 `WEB_DIST_MISSING`。
  - CLI `serve` 实装（Typer → uvicorn，默认 `127.0.0.1:8765`）。
  - 前端：[api.js](../web/src/api.js)、[map.js](../web/src/map.js)（MapLibre + hash 相机 + 相对 source 改写到 `/map/`）、[labels.js](../web/src/labels.js)（按带拉取标签、rank 排序、屏幕空间贪心碰撞）、[main.js](../web/src/main.js)（`window.__app` 探针、`#z/lat/lon` 写回与 hashchange 同步）。
  - 标签为 DOM 层（无字体 glyph，见 ADR-021）；标注点由 style circle 层按 zoom 过滤。
  - 测试：`tests/unit/test_style.py`、`tests/integration/test_server.py`。
- **TASK-0007 详情与 URL 状态（2026-11-19）**：
  - [server/routes.py](../src/mapcreator/server/routes.py)：新增 `GET /api/annotations/{id}`，名称/attrs/描述来自 SQLite（D-016）；`min_zoom/max_zoom` 为 NULL 时返回 kind 默认值（不回写库）；无库 503 `DB_MISSING`、坏库 503 `DB_UNREADABLE`、缺失 404 `ANNOTATION_NOT_FOUND`。
  - [server/app.py](../src/mapcreator/server/app.py)：`create_app(db_path=...)`，默认 `world/annotations.db`。
  - 前端：[ui.js](../web/src/ui.js) 详情面板（全部语种叠加、当前语种高亮、坐标/有效缩放/rank/几何/revision/attrs）；[map.js](../web/src/map.js) 点击查询与 `pointLayers`；[labels.js](../web/src/labels.js) 标签可点击、DOM 选中圆环（WebGL circle filter 在实测中未显示，改用 DOM 环，见 ADR-022）；[main.js](../web/src/main.js) `#z/lat/lon?sel=&lang=` 完整读写与 hashchange 同步、`window.__app.selectedId`。
  - 测试：[test_server.py](../tests/integration/test_server.py) 覆盖详情 200（kind 默认 zoom）、404、503；详情库在 tmp 中通过 `repo.init_schema` + `upsert_annotation` 构造。
- **TASK-0013 UI 外壳（浏览，2026-11-19，纯前端）**：
  - 新增 [shell.js](../web/src/shell.js)（顶栏/左栏/状态栏装配，左栏顺序 图层 → 标注列表 → 世界信息）、[panels.js](../web/src/panels.js)（可折叠分节、开关行、列表行、统计表、空态）、[layers.js](../web/src/layers.js)（把 `build/style.json` 的图层 ID 映射成底图/线状/点标注三组开关）、[shortcuts.js](../web/src/shortcuts.js)（按 `event.code` 绑定，输入控件内不拦截）。
  - 点标注开关联动 [labels.js](../web/src/labels.js) 的 `hiddenKinds`：`setLayoutProperty('visibility')` 关 WebGL 点层的同时剔除 DOM 标签，两者不会不一致；`list()` 暴露当前带标注摘要供左栏列表使用。
  - [index.html](../web/index.html) 重排为地图全幅 + `#topbar` + `#leftbar`（`#sidebar` 保留为右侧详情）；[style.css](../web/src/style.css) 改为深色现代电子地图配色（分节、开关、列表、状态栏），桌面端 ≥1280×720，右侧详情与状态栏无遮挡。
  - [main.js](../web/src/main.js) 装配外壳：选中同步（地图点选/标签点击/列表行三者共用 `select()`）、`Escape` 清选中、带切换时刷新列表、状态栏改由 `shell.setStatus` 输出；`ui.js` 移除 `setStatus`，只保留详情面板。
  - **修复启动崩溃**：生产构建下若 `initMap` 显式传 `zoom: undefined`，MapLibre 的 `jumpTo` 以 `'zoom' in options` 判断，会把它算成 `NaN` 并在 `_calcMatrices` 抛 `failed to invert matrix`，整页白屏。[map.js](../web/src/map.js) 改为「无 center 时不传 zoom」。
  - 浏览模式不挂载任何编辑组件；工具栏/绘制/属性卡仍属 [TASK-0009](TODO.md)。
- **TASK-0009 阶段 A 纯前端编辑器（2026-11-23，已验收）**：
  - 新增 [history.js](../web/src/history.js)（100 份快照、去重、撤销/重做）与 [inspector.js](../web/src/inspector.js)（kind、多语言主名、rank、zoom、description、attrs 及就地校验）；[editor.js](../web/src/editor.js) 接入 Terra Draw 1.40.0 与官方 `terra-draw-maplibre-gl-adapter` 1.5.0，实现选择、点/线/面/矩形、拖拽、顶点编辑、删除和内存草稿。
  - [shell.js](../web/src/shell.js)、[main.js](../web/src/main.js) 与 [index.html](../web/index.html) 接入浏览/编辑模式切换、导出按钮和测试探针；编辑态左栏顺序为工具 → 属性 → 图层 → 标注列表 → 世界信息，右侧详情保持只读。
  - 导出 `annotations.json` 与 `geometry.geojson`；点标注遵守 D-015（仅 lon/lat、无 geometry_id），线/面标注关联 `geo.*`，几何 properties 仅含 kind。既有服务端标注可生成同 ID 的可编辑内存副本，不写后端。
  - 刷新后草稿清空；属性、绘制、拖拽历史可撤销/重做；同绘制模式要素间顶点吸附通过运行时断言。
- **演示世界 `worlds/metro`（2026-11-22，数据集，非产品功能）**：
  - 按用户提供的地铁示意图构造；16 条线路（含 `有軌快車`）、52 个具名站 + 38 个空白椭圆占位站（`label_mode="none"`）、`airport`/`port` 各 1，共 18 个几何 / 107 条标注。
  - 目录结构与 `tests/fixtures/mini-world` 同构：`world.json`、`annotations.json`、`annotations.sql`（逻辑 dump，107 行）、`geometry/*.geojson`；已纳入 git，`annotations.db` 与 `annotations.export.json` 由 `.gitignore` 排除。
  - 构建：`validate --root worlds/metro` ok；`build --root worlds/metro` → `build_version=0.1.0+7158dde243cf`，6 带标签数 `0/0/15/68/68/53`。
  - 持久化：Agent 环境无法创建文件型 SQLite（`CREATE TABLE` 被静默丢弃、库恒 0 字节），改为内存库走 `db/repo.py` 产出 `annotations.sql`；人类终端 `db restore --in worlds/metro/annotations.sql --db worlds/metro/annotations.db` 已物化（147456 B）。
  - 样式修复：[style.py](../src/mapcreator/build/style.py) 的 transit 图层原按几何 `kind` 匹配 `metro_line`（永不命中）且带 `line-dasharray`，导致整网同色虚线；改为 `["coalesce", ["get", "line_color"], palette.metro]` 并去掉虚线，线路按数据配色。
  - 已知偏差：`world.json` 复用 `world.id=aetheria`（构建要求与 `config/world.toml` 一致）；线路走向为示意图近似，未逐段对位。

## 未完成 / 阻塞

| 状态 | 项 | 影响 |
|---|---|---|
| 未做 | `#sel=` 的 Playwright E2E 断言（`window.__app.selectedId` 已就绪） | 目前靠手工浏览器验证，属 TASK-0011 |
| 未复测 | 浏览外壳的 `Ctrl+\` 收起、单个 kind 开关、`重置视图` 按钮、跨带列表刷新 | 均为纯前端行为，代码已就位；需要在真实浏览器手工点一遍 |
| 未做 | `check --full` / `screenshot` / `query` / `openapi` / `format` 仍为占位 | 返回 `NOT_IMPLEMENTED`（退出码 4），属 TASK-0008/0010/0011 |
| 未执行 | 编辑器导出文件的真实 `annotations import` SQLite 写库导入 | 导入共用的 `load_export` 已通过 3 条标注校验；真实写库需由人类终端执行 |
| 未做 | 每带几何裁剪与 source 卸载（当前几何为单一 `unified.geojson`） | 大数据量时的载荷/内存优化，属 TASK-0012 |
| 未做 | CLI `serve` 无 `--db`/`--root` 参数（`create_app` 支持 `db_path` 注入） | 演示世界 `worlds/metro` 的站点详情 404，只能用默认 `world/annotations.db` |
| 未做 | 真实世界内容（`world/` 几何为空） | 真实 `build` 仅含 8 条标注点，暂无几何要素 |
| 未核对 | `docs/ENVIRONMENT.md` 的许可证为初判 | 需人工逐项核对许可证文本 |

## 已知问题与风险

| 问题 | 影响 | 处置 |
|---|---|---|
| ~~本机 D: 盘 SQLite 写入静默丢失~~（**2026-11-19 已定位，非磁盘问题**）：`DELETE`/`WAL` 下 `commit()` 后 DB 0 字节、残留 512 B journal，重开即 `no such table` | 仅影响 **Agent 运行环境**；人类自有终端完全正常（`db init` 成功、106496 字节、无残留） | 根因：Agent 环境拦截文件删除（`os.unlink()` 返回成功但文件仍在），SQLite 的热日志无法清理，下次打开被回滚。**处置：`db`/`annotations` 等写库命令放到人类终端执行**，无需 TRUNCATE/迁盘/白名单 |
| mypy 1.19+ 默认 SQLite 缓存，在本机触发 `no such table: main.files2` 内部错误 | `mypy src` 无法执行 | `pyproject.toml` 设 `sqlite_cache = false`（文件系统缓存）；mypy 2.x 另有版本问题，dev 依赖限制 `<2` |
| `npm ci` 与 `npm install` 不可并发 | 并发会 `ENOTEMPTY`，`.bin` 丢失 | 安装脚本串行执行；失败后删 `node_modules` 重跑 `npm ci` |
| 分支 `feat/civ-atlas-ui` 已推送（`origin/feat/civ-atlas-ui`），但当前工作区仍有未提交改动 | 无历史可回滚到「本轮 UI 改动之前」 | 提交由人类决定；`build/`、`dist/`、DB、截图不入库 |
| 沙箱内 `bash` 起不来（signal pipe 被拒） | `install-deps.sh` 的语法未在本机验证 | 由人类在 Git Bash/WSL 首次运行时确认 |
| Agent 沙箱内 Playwright 使用系统 `%TEMP%` 时可能 `EPERM mkdtemp`，`browser.close()` 也可能卡住 | 默认配置会阻止浏览器启动或退出 | E2E 前把 `TEMP`/`TMP` 指向 `var/tmp`；脚本用 `page.close()` 或 `with sync_playwright()` 收尾，不调用 `browser.close()` |

## 下一步

1. **提交**：由人类审阅并提交 TASK-0013、演示世界与 TASK-0009 阶段 A 改动；`build/`、`web/dist/`、DB、截图和 `var/` 证据不入库。
2. **后续分支**：TASK-0008 搜索与只读 SQL（当前分支不做）。
3. **后续分支**：TASK-0009 阶段 B/C（临时库写端点 → 正式库），届时由人类终端补跑真实导入/写库验收。
4. **TASK-0011**：把 `var/tmp/editor_e2e*.py` 的断言固化为正式 Playwright E2E，并接入 `check --full`；**TASK-0012** 性能优化。

## 最近证据

- TASK-0009 阶段 A 门禁（2026-11-23）：`npm run check` → 20 files、0 问题；`npm run build` → 21 modules、退出码 0（Vite 仅提示 bundle >500 kB）；Python `load_export(var/tmp/editor-export/annotations.json)` → 3 条标注全部通过，ID 为 `anno.city.harbor_point` / `anno.road.main_road` / `anno.park.green_park`，点 geometry_id=None，线/面关联对应几何。未执行真实 SQLite 写库导入。
- TASK-0009 阶段 A 浏览器（Playwright，1280×720，`http://127.0.0.1:8767/`）：主 E2E 34 项 + 补充 E2E 29 项全部通过，console/page 错误均为 `[]`；覆盖浏览态隔离、点/线/面/矩形、属性校验与多语言、拖拽/顶点编辑/吸附、撤销/重做、删除、下载、刷新清空、既有标注内存副本。日志为 `var/tmp/editor_e2e.log`、`var/tmp/editor_e2e_extra.log`；截图为 `var/screenshots/editor-{browse,edit,browse-after,extra,snap}-1280.png`，均已读取核对。
- 演示世界（2026-11-22）：`validate --root worlds/metro --json` → ok（18 几何 / 107 标注）；`build --root worlds/metro --json` → `build_version=0.1.0+7158dde243cf`，6 带标签数 `0/0/15/68/68/53`；内存库 `dump_sql` → `restore_sql` → `verify_dump` 返回 `[]`，dump 54 KB。
- 演示世界浏览器（Playwright，1440×900 / 1280×800，`http://127.0.0.1:8766/`）：`window.__app.ready=true`、状态栏 `z10-12 · z11.00 · Aetheria · 标签 50`、左栏 69 行、无 `PAGEERROR`；16 条线路按 `line_color` 分色；截图 `var/tmp/metro-1440.png`、`var/tmp/metro-1280.png`（已逐张查看）。未验证：站点详情 404（`serve` 未接 `--db`）。
- TASK-0007 门禁：`ruff format --check .` / `ruff check .` / `mypy src` 全绿；`uv run pytest -q` → `46 passed, 1 skipped`（跳过项为 TASK-0011 E2E；唯一 warning 来自 FastAPI TestClient 的第三方弃用提示）；`npm run check` 通过；`npm run build` 产出新 bundle。
- TASK-0013 门禁（前端）：`npm run check` → `Checked 18 files in 245ms. No fixes applied.`；`npm run build` → `dist/assets/index-Dqz9IUYj.js` 820.73 kB（Vite 提示 >500 kB，非错误）。后端未改，Python 门禁沿用 TASK-0007 结果。
- TASK-0013 浏览器（Playwright，1280×720，`http://127.0.0.1:8765/`）：`window.__app.ready=true`；左栏分节顺序 `['图层','标注列表','世界信息']`；左栏底部 664px < 视口 720px（无溢出）；状态栏 `z4-6 · z6.93 · Aetheria · 标签 2`。
- TASK-0013 交互：点列表行「烬堡」→ `selectedId=anno.city.emberhold`、`location.hash=#6.93/9.00581/12.25000?sel=anno.city.emberhold`、右侧详情标题「烬堡」（ZH 烬堡 / EN Emberhold、ID、坐标 13.600000 9.200000、显示缩放 z4–z13、rank 2、点标注无几何、修订 2）；关闭「全部点标注」→ `labels 0 / labelNodes 0`（WebGL 点层与 DOM 标签同步隐藏）；带 `?sel=` 刷新 → 选中与详情面板自动恢复。
- TASK-0013 截图（`var/` 已忽略，不提交）：`var/tmp/1-initial.png`（初始三栏 + 两个标签）、`var/tmp/2-selected.png`（右侧详情）、`var/tmp/3-points-off.png`（点标注关闭）、`var/tmp/4-collapsed.png`（左栏收起）；截图已逐张人工查看。
- TASK-0013 遗留：`Ctrl+\` 收起、单 kind 开关、`重置视图`、跨带列表刷新未单独复测（代码已就位，见「未完成 / 阻塞」）。
- TASK-0007 API：`/api/annotations/anno.city.silverrun` → 200（双语名称、`min_zoom 4 / max_zoom 13`）；`/api/annotations/anno.school.brook` → 200（`12/17`）；缺失 ID → 404 `ANNOTATION_NOT_FOUND`；`db_path` 不存在 → 503 `DB_MISSING`。
- TASK-0007 浏览器：`http://127.0.0.1:8765/?v=9#13.00/8.55/12.08?sel=anno.school.brook&lang=en` → 侧栏标题 "Brook School"、ZH 溪畔小学 主名 / EN Brook School、显示缩放 z12–z17、点选圆环可见、状态栏 `z13-15 · z13.00 · Aetheria · 标签 1 · 选中 anno.school.brook`，地址栏保留 `sel`；截图 `c:\Users\liyunlin\AppData\Local\Temp\trae\screenshots\brook_school_selected.jpg`。
- TASK-0006 门禁：`ruff format --check .` / `ruff check .` / `mypy src` 全绿；`uv run pytest -q` → `44 passed, 1 skipped`；`npm run check` → `Checked 14 files`；`npm run build` → `web/dist`（index + assets）。
- 样式校验：`node` + `@maplibre/maplibre-gl-style-spec` → `style-spec OK`（`build/style.json`）。
- 服务与数据：`/api/health` 200；`/api/world` 200（bounds=`[9.95, 6.95, 14.55, 11.05]`，6 带）；`/api/data/z4-6` 200；`/map/style.json`、`/map/unified.geojson`、`/` 均 200。
- 浏览器证据：`http://127.0.0.1:8765/#6.50/9.00/12.00` → 状态栏 `z4-6 · z6.50 · Aetheria · 标签 2`，可见“烬堡”“银流城”，截图 `c:\Users\liyunlin\AppData\Local\Temp\trae\screenshots\map_z6_50.jpg`；`#13.00/8.60/12.10` → 状态栏 `z13-15 · z13.00 · 标签 1`，可见“旧港博物馆”，截图 `...\z13_label_check.jpg`。
- 真实路径 DB 往返（人类终端，2026-11-19）：`annotations import` → `count: 8`；`db dump` → `world/annotations.sql`（5489 B）；`db restore` → ok；`db verify-dump` → `checked: logical-tables`；`annotations.db` 114688 B、无残留 journal。
- `uv run pytest -q` → `38 passed, 1 skipped`（跳过项为 TASK-0011 的 E2E）；`ruff format --check .` → `106 files already formatted`；`ruff check .` → `All checks passed!`；`mypy src` → `Success: no issues found in 31 source files`。
- `uv run mapcreator validate --root tests/fixtures/mini-world --json` → `ok: true`，bounds=`[9.95, 6.95, 14.55, 11.05]`，6 几何 / 8 标注，6 个带标签数 `0/2/3/5/8/5`。
- 构建产物（mini-world）：`unified.geojson`、`annotations.export.json`、`data/labels.{z0-3,z4-6,z7-9,z10-12,z13-15,z16-17}.geojson`、`manifest.json`；两次构建后目录总哈希一致；模拟失败后旧 `build/` 哈希不变。
- `uv run mapcreator build --root tests/fixtures/mini-world --json` → `ok: true`，`build_version=0.1.0+196d4865108f`，9 个 artifact，`manifest.files` 均含 sha256。
- **SQLite 定位证据**：`D:` 为固定 NTFS、Healthy；普通文件写 + `fsync` 正常；`os.unlink()` 对工作区文件返回成功但文件仍存在（`%TEMP%` 下删除正常）→ 热日志残留导致回滚。**写库命令在人类终端执行即正常。**
- 早前基线：`doctor --json` 全绿；`npm ci` → `added 55 packages`；`npm run build` → `web/dist/index.html`；`uv sync --locked` 锁文件一致。
- 未验证：`install-deps.sh` 语法（沙箱 `bash` 限制）；许可证逐项核对（人工）；真实世界几何内容（`world/` 仍为空，属内容任务）。
