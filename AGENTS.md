# AGENTS.md — AI Agent 唯一入口

> 项目：MapCreator（本地优先、Python 主导、可缩放分级标注的架空世界地图）
> 状态：**设计已确认（v0.2），M0 未开始，代码尚不存在**
> 本文件是唯一入口。`CLAUDE.md` 只是指向这里；其余信息一律通过路径链接获取，不在这里复制。

---

## 0. 开工前必读

当前仓库有骨架代码与部分业务实现：`doctor`、`describe`、`schema`、`db`/`annotations`、`validate`、`build`、`serve` 可用；**TASK-0003 ~ TASK-0007 已完成**，下一步 TASK-0013（浏览外壳）；编辑器按原顺序留在 TASK-0009（含临时库 `var/editor-test/`），方案见 `docs/CIV_ATLAS_UI_PORT.md`。
**Agent 环境会拦截文件删除**（`os.unlink` 返回成功但文件仍在），导致 SQLite 热日志残留、写库失败；因此 `db`/`annotations` 等**写库命令必须由人类在自己的终端执行**。跑 pytest 前若遇到 `no such table: main.annotation_name`，先删掉仓库根的 `pytest-of-*/` 再用 PowerShell 重跑（残留热日志导致）。
第 3 节命令表中标注"未实现"的仍是占位，不要凭记忆调用。

## 1. 阅读顺序

1. 本文件（规则与边界）。
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)（分层、数据流、API）。
3. [`docs/DATA_SPEC.md`](docs/DATA_SPEC.md)（坐标、ID、GeoJSON、SQLite、校验）。
4. [`docs/STATUS.md`](docs/STATUS.md)（做到哪了、有什么坑）。
5. [`TODO.md`](TODO.md) 中当前任务的条目。
6. 按需：`docs/EDITOR.md`、`docs/TESTING.md`、`docs/DEPENDENCIES.md`、`docs/DECISIONS.md`、`docs/ENVIRONMENT.md`。

核心上下文（1–5）目标 ≤ 600 行。若发现某份文档 > 250 行，先考虑拆分而不是继续加长。

## 2. 不可协商的规则

1. **单一写路径**：所有数据写入必须经过 Python 校验层（CLI 或 FastAPI）。禁止浏览器直写文件/数据库，禁止绕过 `db/repo.py`。
2. **ID 是契约**：几何 `geo.<kind>.<slug>`，标注 `anno.<kind>.<slug>`；ID 一旦创建不再改变（可改名，不可改 ID）。
3. **名称只在 SQLite**（D-016）：GeoJSON 与前端真源不存 `name`；多语言名称存 `annotation_name` 子表；渲染分片由构建期从 DB **生成**（派生物，可重建）。
4. **点标注不建几何**（D-015）：点坐标只存 `annotation.lon/lat`，`geometry_id` 恒为 NULL。线/面标注才关联几何。
5. **缩放带边界只在 `config/zoom_bands.toml`**（D-018）：6 个固定带；`kinds.toml` 的 zoom 区间只产生 style filter，绝不反推带。
6. **确定性构建**：稳定排序、坐标 6 位小数、固定缩进、**无时间戳**；同输入同版本 → 字节级一致。
7. **不重复造轮子**：先查 `docs/ARCHITECTURE.md` 的复用清单；自研引擎/编辑器/切片/表单/搜索前必须先写 ADR（`docs/DECISIONS.md`）。
8. **不手工编辑生成物**：`build/`、`dist/`、`web/dist`、`docs/openapi.json` 只由命令生成。
9. **无证据不算完成**：见第 6 节 DoD。
10. **不擅自变更【已定】决策**：改 D-001–D-021 之前必须先问人类。
11. **不做未经批准的联网动作**：不要在任务里顺手 `git clone`、`pip install`、`npm install`、`uv sync`、`playwright install`。安装/拉取必须由人类明确批准，并按 `docs/ENVIRONMENT.md` 的清单执行。

## 3. 命令（TASK-0002 之后可用）

| 命令 | 用途 | 状态 |
|---|---|---|
| `uv run mapcreator doctor --json` | 环境自检 + 修复建议 | 已实现 |
| `uv run mapcreator describe --json` | 世界概览：范围、kind、计数 | 已实现 |
| `uv run mapcreator schema --out schemas` | 从模型导出 JSON Schema | 已实现 |
| `uv run mapcreator db init\|dump\|restore\|verify-dump` | 数据库建库与逻辑 dump 往返 | 已实现（写库须在人类终端） |
| `uv run mapcreator annotations export\|import` | 标注导入导出 | 已实现（同上） |
| `uv run mapcreator validate --json` | 只校验，不写产物 | 已实现 |
| `uv run mapcreator build --json` | 全量构建（`.tmp-build` → 原子替换） | 已实现（`--watch` 未接入） |
| `uv run mapcreator serve` | 本地应用（`127.0.0.1:8765`；先 `npm run build` 与 `build`） | 已实现 |
| `uv run mapcreator check --full --json` | 格式/类型/单测/校验/构建/E2E | 未实现 |
| `uv run mapcreator screenshot --url ... --out ...` | 截图证据 | 未实现 |
| `uv run mapcreator query --sql ... --json` | 只读 SQL | 未实现 |
| `uv run mapcreator openapi --out docs/openapi.json` | 导出 API 契约 | 未实现 |

统一约定：所有命令支持 `--json`，输出 `ok / command / duration_ms / errors[] / warnings[] / artifacts[]`；退出码 `0` 成功、`1` 数据失败、`2` 用法错误、`3` 环境缺失、`4` 内部错误。

## 4. 数据速查（细节见 DATA_SPEC）

- 坐标：RFC 7946 经纬度（虚构地理），精度 6 位小数，不跨 ±180°。
- 世界：小范围有界区域、二维俯视；`bounds` 由构建从数据推导（`world.toml` 可覆盖）；`max_zoom = 17`。
- GeoJSON `properties` 只允许白名单键（`kind`、`width_class`、`road_class`…），**不写 `name`、不写 `layer`**。
- 标注字段：`kind / lon / lat / rank / min_zoom / max_zoom / icon / description / attrs / parent_id / geometry_id / revision / deleted_at`。
- `min_zoom/max_zoom` 为 NULL = 用 kind 默认值；构建期回填，**不写回库**。
- 软删除：`deleted_at`；查询永远 `AND deleted_at IS NULL`。

## 5. 代码约定速查

- Python：全量类型注解；公共函数 docstring 写契约；单文件 < 300 行；副作用只在 CLI/API 边界；异常带 `code/path/feature_id/remediation`；外部命令用 `subprocess.run([...])`，不拼 shell。
- JS：原生 ES 模块 + `// @ts-check` + JSDoc；Biome 统一格式；`main.js` 只启动、`map.js` 管地图、`api.js` 管请求、`editor.js` 管绘制、`ui.js` 管面板；测试模式暴露 `window.__app`（`ready`/`zoom`/`visibleLabelCount`）。
- 文件：`pathlib.Path`、显式 `encoding="utf-8"`、`.gitattributes` 统一 LF、不靠大小写区分文件名。

## 6. Definition of Done

- [ ] 行为已实现，且有测试（单元/集成/E2E 至少一种）；边界与错误路径覆盖。
- [ ] `uv run mapcreator check --full --json` 通过（M0 前用等价的 pytest/ruff/mypy 命令，并在报告里说明）。
- [ ] schema/数据/API 变更同步文档与 golden 文件。
- [ ] DB 变更含迁移与 `schema_version` 更新。
- [ ] UI 变更附截图，且**自己读过截图**确认。
- [ ] 未超性能预算；超了要有测量数据 + ADR。
- [ ] 新依赖已登记 `docs/DEPENDENCIES.md`；未手工改生成物；未提交 `build/`、`dist/`、DB、截图。
- [ ] `docs/STATUS.md` 已更新；重大决策进 `docs/DECISIONS.md`。
- [ ] 错误信息含路径/ID/修复建议。

## 7. 任务循环

1. 读第 1 节文档 + 当前任务。
2. 环境自检（`doctor`；尚不存在时说明替代检查方式）。
3. 计划：将改动的文件、验收测试、风险；有歧义**先问**。
4. 实现：小而完整的垂直切片，不夹带无关重构。
5. 验证：跑检查；UI 截图并查看。
6. 记录：`STATUS.md` / ADR / `DEPENDENCIES.md`。
7. 报告：见第 8 节。

## 8. 报告格式（缺一不可）

```text
摘要：一句话说清做成什么
修改文件：<路径列表>
命令与结果：<命令> → <关键输出/退出码>
证据：<截图路径 / manifest 计数 / 测试输出>
未验证项及原因：<明确写出，不许省略>
风险与下一步：<可否继续下一个任务>
```

## 9. 禁止（反模式）

- 编造库 API（必须先查锁定版本的文档/类型/源码）。
- 改生成文件后声称修好；手写巨大 style JSON。
- 为小功能引入大框架；引入两个功能重复的库。
- 静默吞异常、只打印 `error`。
- 构建输出带时间戳导致不可重复。
- 跳过截图/测试就报告完成。
- 在未确认 §18.2 项目（静态导出范围、真实世界内容、图标选型、撤销历史持久化、多世界）时自行定方案。

## 10. 何时必须停下来问人类

- 要修改 D-001–D-021 中任一【已定】决策。
- 要新增依赖、自研组件、或执行任何安装/克隆/下载。
- 要删除或重写真源数据（`world/`、`annotations.sql`）。
- 触及 §18.2 未确认项，或出现两种都能自洽的实现路线。
- 发现文档自相矛盾（例：同一字段两处定义不同）。

## 11. 目录导航

| 想知道 | 看 |
|---|---|
| 系统怎么分层、模块边界 | `docs/ARCHITECTURE.md` |
| 字段/表/校验/坐标/ID | `docs/DATA_SPEC.md` |
| 编辑器与 QGIS 往返 | `docs/EDITOR.md` |
| 测试怎么写、门禁是什么 | `docs/TESTING.md` |
| 依赖版本与许可证 | `docs/DEPENDENCIES.md` |
| 装什么、从哪来（只列不装） | `docs/ENVIRONMENT.md` |
| 为什么这样定 | `docs/DECISIONS.md` |
| 现在到哪一步 | `docs/STATUS.md` |
| 接下来做什么 | `TODO.md` |
