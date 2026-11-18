# 项目状态（STATUS）

- **当前里程碑**：M0（骨架与契约）——**进行中：依赖已安装、`doctor` 已实现，业务功能未开始**
- **最近更新**：2026-11-18
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

## 未完成 / 阻塞

| 状态 | 项 | 影响 |
|---|---|---|
| 未做 | 除 `doctor` 外，`mapcreator` 子命令仍为占位 | 返回 `NOT_IMPLEMENTED`（退出码 4） |
| 未做 | `world/annotations.sql` 与工作库 | 需 TASK-0004 的 `db` 子命令 |
| 未做 | mini-world 内容（目前只有 README） | golden/E2E 无基准数据 |
| 未核对 | `docs/ENVIRONMENT.md` 的许可证为初判 | 需人工逐项核对许可证文本 |

## 已知问题与风险

| 问题 | 影响 | 处置 |
|---|---|---|
| 本机 `D:\Git_Projects\MapCreator` 下 SQLite **写入静默丢失**：`DELETE`（默认）与 `WAL` 模式下 `CREATE/INSERT` + `commit()` 不落盘（DB 0 字节、残留 `-journal`、重开为空）；`TRUNCATE`/`PERSIST`/`MEMORY`/`OFF` 正常，`:memory:` 正常，普通文件写入 + `fsync` + 删除也正常 | `DATA_SPEC` 计划用 WAL → TASK-0004 在本机可能失败 | **已决定（2026-11-18）：先搁置，直到 TASK-0004 真正写库撞墙再处理。** 撞墙时的备选：① `journal_mode=TRUNCATE`；② 仓库迁到 C:；③ 给 D:\Git_Projects 加杀软/同步盘白名单。任选其一并写 ADR |
| mypy 1.19+ 默认 SQLite 缓存，在本机触发 `no such table: main.files2` 内部错误 | `mypy src` 无法执行 | `pyproject.toml` 设 `sqlite_cache = false`（文件系统缓存）；mypy 2.x 另有版本问题，dev 依赖限制 `<2` |
| `npm ci` 与 `npm install` 不可并发 | 并发会 `ENOTEMPTY`，`.bin` 丢失 | 安装脚本串行执行；失败后删 `node_modules` 重跑 `npm ci` |
| 还没创建首次 git commit | 无历史可回滚 | remote 已配置为 `origin` → `https://github.com/Evan5321/MapCreator.git`（远端为空）；首次提交由人类确认后执行 |
| 沙箱内 `bash` 起不来（signal pipe 被拒） | `install-deps.sh` 的语法未在本机验证 | 由人类在 Git Bash/WSL 首次运行时确认 |
| Agent 沙箱内 Playwright 启动失败：`EPERM mkdtemp`（`%TEMP%` 不可写） | 我无法在 Agent 内跑通浏览器启动/E2E | 二进制已就位；由人类在自己的终端跑一次启动验证 |

## 下一步

1. 人类手动：在自终端验证 Chromium 可启动、核对 `ENVIRONMENT.md` 许可证、确认首次提交并 `git push -u origin main`。
2. **TASK-0003**：Pydantic 配置模型接入 4 个 TOML；生成 mini-world。
3. **TASK-0004**：数据库层。SQLite 写丢失问题**按决定搁置**，先按计划实现；真正写库失败（撞墙）时再按「已知问题」里的三个备选处置。

## 最近证据

- `uv run mapcreator doctor --json` → `ok: true`，必需项全绿；退出码 0；Playwright 检测为 ok；告警仅剩可选工具（pwsh/QGIS/Docker/tippecanoe）。
- `uv run ruff format --check .` / `ruff check .` → 通过；`uv run mypy src` → `Success: no issues found in 23 source files`。
- `uv run pytest -q` → `6 passed, 2 skipped`（含 doctor 单测 5 条；跳过项为 TASK-0005/TASK-0011 占位）。
- `npm ci` → `added 55 packages`，退出码 0；`npm run check` → `Checked 27 files`，无错误。
- `npm run build` → `web/dist/index.html`（598 B）+ `assets/index-*.js`（803 kB，gzip 218 kB）。
- `uv sync --locked` → `Resolved 46 packages` / `Checked 45 packages`，锁文件一致。
- 未验证：`install-deps.sh` 语法（沙箱 `bash` 限制）；许可证逐项核对（人工）；SQLite 写丢失的根因（需在 C: 与 D: 各复现一次，见「已知问题」）。
