# TODO List

> 这是**唯一**的任务清单。`docs/STATUS.md` 只记录"做到哪了"，本文件记录"要做什么"。
> 每个任务都必须满足 [`AGENTS.md`](AGENTS.md) 第 6 节 DoD 才能标记完成。
> 状态：`[ ]` 未开始 · `[~]` 进行中 · `[x]` 完成 · `[!]` 阻塞

## 里程碑

| 里程碑 | 交付物 | 验收标准 | 状态 |
|---|---|---|---|
| **M0 骨架与契约** | 仓库结构、CLI 骨架、config、schema、mini-world、`doctor`/`check`、Web 构建 | `doctor` 全绿；`check` 通过；`serve` 显示可缩放样例 | `[~]` |
| **M1 浏览与分级标注** | 构建合并视图、MapLibre 页面、缩放带、点/线标注、碰撞、点选详情、URL 状态 | z0→z17 正常；标注按规则出现/消失；无控制台错误 | `[ ]` |
| **M2 搜索与 SQL** | FTS5/RTree、搜索 API/UI、只读 SQL、导入导出、dump/restore | 中/英/别名可搜（含 2 字词）；dump 往返一致 | `[ ]` |
| **M3 编辑器** | Terra Draw 点/线/面、属性表单、保存校验、撤销/重做、软删除 | 三类几何可增删改；非法输入被拒；刷新可见 | `[ ]` |
| **M4 交通与运维** | relation、地铁/公交线路与有序站点、QGIS 往返、批量导入、审计日志 | 5 站线路可渲染；往返不丢字段 | `[ ]` |
| **M5 性能与分发** | 分片优化、简化、可选 PMTiles、性能基准、打包说明 | 性能预算达标；文档完整 | `[ ]` |

---

## M0 骨架与契约

### `[~]` TASK-0001 仓库骨架

- **Goal**：让仓库可运行、可检查、可提交。
- **Scope**：`pyproject.toml`、`uv.lock`、`package.json`、`package-lock.json`、`biome.json`、`ruff`/`mypy` 配置、`vite` 骨架、`.gitignore`、`.gitattributes`、`git init`。
- **Out of scope**：任何业务功能、任何 `mapcreator` 子命令。
- **Acceptance**：
  - [x] 目录树、`pyproject.toml`、`package.json`、`biome.json`、`.gitignore`、`.gitattributes`、`.editorconfig`、`git init` 完成。
  - [x] 骨架一致性静态校验通过（27 kind、6 band、JSON/Python 语法、kind→schema/palette 引用）。
  - [x] `uv sync` 可复现；`uv.lock` 已提交（46 包，2026-11-18 安装）。
  - [x] `npm ci` 可复现；`package-lock.json` 已提交（55 包，2026-11-18 安装）。
  - [x] `ruff check` / `ruff format --check` / `mypy src` 通过。
  - [x] `npm run build` 产出 `web/dist/index.html`。
  - [x] `.gitignore` 排除 `build/`、`dist/`、`web/dist/`、`*.db`、`artifacts/`、`logs/`、`node_modules/`、`.venv/`。
  - [ ] `docs/ENVIRONMENT.md` 的许可证与版本已逐项核对并改为确定值。
- **阻塞**：仅剩许可证核对（人工）；依赖已安装，重装用 `scripts/install-deps.ps1`。
- **Evidence**：`doctor --json` 全绿；`ruff`/`mypy`/`pytest`/`npm run build` 输出见 `docs/STATUS.md`「最近证据」。
- **Deps**：无

### `[x]` TASK-0002 CLI 与 `doctor`

- **Goal**：一个入口、统一 JSON、稳定退出码。
- **Scope**：`src/mapcreator/cli.py`、`errors.py`、`config.py` 骨架；`doctor` 子命令。
- **Acceptance**：
  - [x] `uv run mapcreator --help` 列出全部子命令。
  - [x] `doctor --json` 输出 Python/uv/Node/npm 版本、SQLite FTS5/RTree/trigram、Playwright、可选工具（QGIS/Docker/tippecanoe）。
  - [x] 缺失项给出 `remediation`；退出码按 9.5（0/1/2/3/4）。
  - [x] 同一输出结构有单测（fixture 模拟缺失项）。
- **Evidence**：`doctor --json` 输出（必需项全绿、退出码 0）；`tests/unit/test_doctor.py` 5 条用例。
- **Deps**：TASK-0001

### `[x]` TASK-0003 配置与 schema

- **Scope**：`config/world.toml`、`kinds.toml`（27 个 kind）、`zoom_bands.toml`（6 带）、`palette.toml`；`schemas/*.json`；`world/world.json`；`tests/fixtures/mini-world/`。
- **Acceptance**：
  - [x] 4 个 TOML 可被 Pydantic 加载，非法值报错含字段路径。
  - [x] JSON Schema 由模型导出（`schemas/*.schema.json`），与 `DATA_SPEC` 一致。
  - [x] mini-world 满足 `DATA_SPEC`（1 大陆、1 海、2 河、1 山脉、2 城、5 POI、1 地铁线）。
  - [x] `mapcreator describe --json` 输出计数与 bounds。
- **Evidence**：schema 文件、`describe --json`。
- **Deps**：TASK-0002

### `[x]` TASK-0004 数据库层

- **Scope**：`src/mapcreator/db/schema.sql`、`migrations/`、`repo.py`；`annotation_name`；FTS/RTree 触发器；dump/restore/verify。
- **Acceptance**：
  - [x] `db restore` → `db verify-dump` → `db dump` 往返一致（逻辑表字节级）。
  - [x] 名称 `is_primary` 唯一约束生效；缺主名被拒。
  - [x] `search_text` 与名称表不一致时 `verify-dump` 失败。
  - [x] 触发器维护 FTS/RTree；软删除后查询过滤正确。
  - [x] 搜索：2 字走 LIKE、3 字走 MATCH，均有单测。
  - [x] 上述往返在**真实路径** `world/annotations.db` 上通过（人类终端，2026-11-19）。
- **环境备注**：曾出现 `db init` 退出码 4（`no such table: main.annotation_name`、DB 0 字节 + 512 B 残留 journal）。定位为 **Agent 运行环境拦截文件删除**（`os.unlink` 返回成功但文件仍在）→ SQLite 热日志残留、重开回滚；磁盘与 SQLite 本身正常。**写库命令请在人类终端执行**；无需 TRUNCATE/迁盘/白名单。
- **Evidence**：`annotations import` → `count: 8`；`db dump` → `world/annotations.sql`（5489 B、`schema_version: 1`）；`db restore` → ok；`db verify-dump` → `checked: logical-tables`；`annotations.db` 114688 B；pytest `38 passed, 1 skipped`。
- **Deps**：TASK-0003

### `[x]` TASK-0005 构建合并

- **Scope**：`build/pipeline.py`、`bands.py`、`manifest.py`；原子发布。
- **Acceptance**：
  - [x] `validate` 只校验不产物；`build` 产物落在 `.tmp-build/` 后原子替换（失败保留上次产物）。
  - [x] 合并视图 `build/unified.geojson` 与 `build/annotations.export.json` 生成。
  - [x] `manifest.json` 含输入哈希、计数、`build_version`、推导 bounds，**无时间戳**。
  - [x] 同输入连跑两次产物字节一致（除字体/图标）。
- **Evidence**：`tests/unit/test_build.py`、`tests/integration/test_build_mini_world.py`；`pytest` 38 passed / 1 skipped；`validate --root tests/fixtures/mini-world --json` → 6 几何 / 8 标注，6 个带标签数 0/2/3/5/8/5。
- **Deps**：TASK-0004

### `[x]` TASK-0006 样式与前端地图

- **Scope**：`build/style.py`、`web/src/{main,map,api,ui}.js`、`styles/base.maplibre.json`。
- **Acceptance**：
  - [x] `serve` 打开显示可缩放地图，`#z/lat/lon` 生效（含同页 hash 变化同步）。
  - [x] 6 个带按边界加载/卸载标签分片（`/api/data/{band}`）；带内按 `kinds.toml` 的 kind 区间生成 `minzoom/maxzoom`（D-018）。几何统一源 + 每带裁剪/卸载策略留 TASK-0012。
  - [x] 点标注按 rank 与 zoom 显示；标签按 rank 排序并做屏幕空间贪心碰撞（ADR-021）。
  - [x] 样式通过 style-spec 校验；截图已查看。
- **Evidence**：`z6.50` 截图（标签 2：烬堡/银流城）；`z13.00` 截图（band z13-15、标签显示）；style-spec `style-spec OK`；详见 `docs/STATUS.md`。
- **Deps**：TASK-0005

## M1 浏览与分级标注

### `[x]` TASK-0007 详情与 URL 状态

- **Scope**：点选 → `/api/annotations/{id}` → 详情面板；`#sel=`；多语言显示 `#lang=`。
- **Acceptance**：
  - [x] 点选（圆点或 DOM 标签）→ 侧栏详情 + 选中圆环；点空白处关闭。
  - [x] `#z/lat/lon?sel=<id>&lang=<lang>` 可复制还原；选中后 hash 保留 `sel`。
  - [x] 详情叠加全部语种名称，`#lang=` 决定标题语种（zh→溪畔小学 / en→Brook School）。
  - [x] 详情含有效 zoom（NULL 回填 kind 默认，不回写库）、坐标、rank、几何、revision、attrs。
  - [ ] E2E 断言 `selectedId`（`window.__app` 已暴露，属 TASK-0011 Playwright）。
- **Evidence**：`/api/annotations/anno.school.brook` → 200（`min_zoom 12 / max_zoom 17`、双语名称）；缺失 ID → 404 `ANNOTATION_NOT_FOUND`；无 DB → 503 `DB_MISSING`；截图 `brook_school_selected.jpg`（侧栏 Brook School + 双语 + 圆环 + 状态栏 `选中 anno.school.brook`）。
- **Deps**：TASK-0006

## M2 搜索与 SQL

### `[ ]` TASK-0008 搜索

- **Scope**：`/api/search`、搜索 UI、flyTo+高亮、`/api/query`（`--enable-sql`）。
- **Acceptance**：中/英/别名/2 字词可搜；p95 ≤ 100 ms；只读 SQL 拒绝非 SELECT；非法 SQL 有明确错误。
- **Deps**：TASK-0007

## M3 编辑器

### `[ ]` TASK-0009 编辑器

- **Scope**：`web/src/editor.js`（Terra Draw）、JSON Editor 表单、写接口、撤销/重做、软删除、409 冲突。
- **Acceptance**：见 [`EDITOR.md`](docs/EDITOR.md) §9 全部勾选。
- **Deps**：TASK-0008

## M4 交通与运维

### `[ ]` TASK-0010 relation 与 QGIS 往返

- **Scope**：`relation`/`relation_member` CRUD、线路渲染、`export --qgis` / `import`、`format`、审计日志。
- **Acceptance**：5 站线路可创建并渲染；往返不丢 `attrs`/`names`/`rank`/zoom（golden 守）。
- **Deps**：TASK-0009

## M5 性能与分发

### `[ ]` TASK-0011 测试与证据收口

- **Scope**：golden 全量、Playwright E2E、`check --full`、`artifacts/perf.json`。
- **Acceptance**：`check --full` 一条命令覆盖格式/类型/单测/校验/构建/E2E；性能基线入库。
- **Deps**：TASK-0009

### `[ ]` TASK-0012 性能优化

- **Scope**：实测后调 `simplify_tolerance`、每带裁剪策略、source 卸载策略。
- **Acceptance**：`docs/TESTING.md` §5 全部预算达标，或有 ADR 说明例外。
- **Deps**：TASK-0011

---

## 待决策（未确认前不得实现）

| 项 | 说明 | 阻塞 | 处置 |
|---|---|---|---|
| `[ ]` 静态导出 | 是否含搜索、目标包体 | M5 之后 | 需要人类确认（§18.2 #1） |
| `[ ]` 真实世界内容 | 地名、密度、首批地区 | M1 之后 | 需要人类提供数据或生成规则 |
| `[ ]` 图标集选型 | 视觉规格、许可证 | 不阻塞 | 先用 Maki 风格占位 |
| `[ ]` 撤销历史持久化 | 是否跨会话保留 | M3 | 先只做会话内 |
| `[ ]` 多世界 | 是否支持切换 `world/` | 不阻塞 | 先假定单世界 |

## 与 v0.2 契约的编号映射

`DEVELOPMENT_PREP.md` §12.2 列了 10 个任务（0001–0010），这里拆成 12 个：把"详情与 URL 状态"从原 TASK-0006 中独立、把"性能优化"从原 M5 中独立。对应关系：

| 原编号 | 本文件 |
|---|---|
| 0001 仓库骨架 | TASK-0001 |
| 0002 CLI 与 doctor | TASK-0002 |
| 0003 配置与 schema | TASK-0003 |
| 0004 数据库层 | TASK-0004 |
| 0005 构建合并 | TASK-0005 |
| 0006 样式与前端地图 | TASK-0006 + TASK-0007 |
| 0007 搜索 | TASK-0008 |
| 0008 编辑器 | TASK-0009 |
| 0009 测试与证据 | TASK-0011 |
| 0010 QGIS 往返 + 文档收尾 | TASK-0010 |
| （新增）性能优化 | TASK-0012 |

## 维护规则

- 完成任务时：勾选本文件 → 更新 `docs/STATUS.md` → 必要时在 `docs/DECISIONS.md` 追加 ADR。
- 新任务必须写清 Goal/Scope/Out of scope/Acceptance/Evidence/Deps。
- 一个任务一个垂直切片；不把"重构"塞进功能任务。
- 发现任务描述与 `DATA_SPEC` 冲突时，先改文档再写代码（spec-first）。
