# 项目状态（STATUS）

- **当前里程碑**：M1（浏览与分级标注）——**TASK-0003 ~ TASK-0007 完成**，`serve` 可浏览分级地图并点选查看详情
- **最近更新**：2026-11-19
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

## 未完成 / 阻塞

| 状态 | 项 | 影响 |
|---|---|---|
| 未做 | `#sel=` 的 Playwright E2E 断言（`window.__app.selectedId` 已就绪） | 目前靠手工浏览器验证，属 TASK-0011 |
| 未做 | `check --full` / `screenshot` / `query` / `openapi` / `format` 仍为占位 | 返回 `NOT_IMPLEMENTED`（退出码 4），属 TASK-0008/0010/0011 |
| 未做 | 每带几何裁剪与 source 卸载（当前几何为单一 `unified.geojson`） | 大数据量时的载荷/内存优化，属 TASK-0012 |
| 未做 | 真实世界内容（`world/` 几何为空） | 真实 `build` 仅含 8 条标注点，暂无几何要素 |
| 未核对 | `docs/ENVIRONMENT.md` 的许可证为初判 | 需人工逐项核对许可证文本 |

## 已知问题与风险

| 问题 | 影响 | 处置 |
|---|---|---|
| ~~本机 D: 盘 SQLite 写入静默丢失~~（**2026-11-19 已定位，非磁盘问题**）：`DELETE`/`WAL` 下 `commit()` 后 DB 0 字节、残留 512 B journal，重开即 `no such table` | 仅影响 **Agent 运行环境**；人类自有终端完全正常（`db init` 成功、106496 字节、无残留） | 根因：Agent 环境拦截文件删除（`os.unlink()` 返回成功但文件仍在），SQLite 的热日志无法清理，下次打开被回滚。**处置：`db`/`annotations` 等写库命令放到人类终端执行**，无需 TRUNCATE/迁盘/白名单 |
| mypy 1.19+ 默认 SQLite 缓存，在本机触发 `no such table: main.files2` 内部错误 | `mypy src` 无法执行 | `pyproject.toml` 设 `sqlite_cache = false`（文件系统缓存）；mypy 2.x 另有版本问题，dev 依赖限制 `<2` |
| `npm ci` 与 `npm install` 不可并发 | 并发会 `ENOTEMPTY`，`.bin` 丢失 | 安装脚本串行执行；失败后删 `node_modules` 重跑 `npm ci` |
| 还没创建首次 git commit | 无历史可回滚 | remote 已配置为 `origin` → `https://github.com/Evan5321/MapCreator.git`（远端为空）；首次提交由人类确认后执行 |
| 沙箱内 `bash` 起不来（signal pipe 被拒） | `install-deps.sh` 的语法未在本机验证 | 由人类在 Git Bash/WSL 首次运行时确认 |
| Agent 沙箱内 Playwright 启动失败：`EPERM mkdtemp`（`%TEMP%` 不可写） | 我无法在 Agent 内跑通浏览器启动/E2E | 二进制已就位；由人类在自己的终端跑一次启动验证 |

## 下一步

1. **TASK-0008**：搜索与只读 SQL（`/api/search`、`/api/query`）。
2. **TASK-0011**：Playwright E2E（`window.__app.selectedId` 断言、启动验证）。
3. 人工项（可并行）：Chromium 启动验证、`ENVIRONMENT.md` 许可证核对、首次提交与 `git push -u origin main`。

## 最近证据

- TASK-0007 门禁：`ruff format --check .` / `ruff check .` / `mypy src` 全绿；`uv run pytest -q` → `46 passed, 1 skipped`（跳过项为 TASK-0011 E2E；唯一 warning 来自 FastAPI TestClient 的第三方弃用提示）；`npm run check` 通过；`npm run build` 产出新 bundle。
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
