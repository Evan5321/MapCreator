# MapCreator

> 本地优先、Python 主导、**可缩放分级标注**的架空世界地图浏览与编辑工具。几何用 GeoJSON 描述，标注与多语言名称用 SQLite 管理，复用 MapLibre GL JS 与 Terra Draw，不自己造地图引擎。

**当前状态：M0 进行中——依赖已安装（`uv.lock` / `package-lock.json` 已生成），`doctor` 已可用，业务子命令仍是占位。**
`uv run mapcreator doctor --json` 可自检环境；其余 `mapcreator` 子命令仍返回 `NOT_IMPLEMENTED`（退出码 4）。
重装依赖用 `scripts/install-deps.ps1`（或 `.sh`）。

---

## 它解决什么问题

做一张自己的世界地图，通常会在两个极端之间卡住：

- 纯手绘/矢量软件：好看，但不可查询、不可 diff、AI 读不懂；
- 真 GIS/瓦片栈：强大，但工具链重、Windows 上坑多、为一张小地图过度建设。

MapCreator 的取舍是：**几何进 GeoJSON（AI 可读、可 diff），标注进 SQLite（可 SQL、可 FTS5 全文检索、可空间索引）**，渲染交给 MapLibre，编辑交给 Terra Draw，构建/校验/服务全部用 Python 一个入口命令完成。

## MVP 范围

- 缩放/平移、世界边界限制、URL 状态（`#z=&lat=&lon=&sel=`）。
- 7 个几何图层：陆地、水域、河流、地形、道路、轨道、公园。
- 点/线标注按**缩放带**分级显示，带碰撞避让与图标。
- 搜索：中文、英文、别名、多语言名称（FTS5 trigram + 短词回退）。
- 点选详情、结果定位与高亮。
- Web 编辑器：点/线/面创建与编辑、属性表单、保存校验、撤销/重做、软删除。
- 一条命令完成校验 → 构建 → 启动 → 截图。

**当前阶段不做**：真实地理精度、导航/路径规划、多人在线、账号权限、移动 App、3D、自研渲染引擎/瓦片服务器/绘制库、浏览器内强拓扑编辑。

## 技术栈

| 层 | 选型 |
|---|---|
| 语言 | Python 3.12+（后端、构建、CLI、测试） |
| 环境/依赖 | `uv` + `uv.lock` |
| CLI | Typer |
| 本地服务 | FastAPI + Uvicorn（单进程，`127.0.0.1`） |
| 校验 | Pydantic v2 + `geojson-pydantic` + Shapely |
| 存储 | SQLite（stdlib `sqlite3`，FTS5 trigram + R*Tree） |
| 渲染 | MapLibre GL JS |
| 绘制 | Terra Draw |
| 前端 | Vite + 原生 ES 模块 + JSDoc（**不用框架、不用 TS**） |
| 测试 | pytest + Playwright（Python 驱动） |

完整清单（含每个库的 GitHub 地址、许可证、安装形态）见 [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)；运行时依赖登记规则见 [`docs/DEPENDENCIES.md`](docs/DEPENDENCIES.md)。

## 文档地图

| 文件 | 内容 | 先读谁 |
|---|---|---|
| [`AGENTS.md`](AGENTS.md) | **AI Agent 唯一入口**：阅读顺序、命令、硬规则、DoD | AI、贡献者 |
| [`TODO.md`](TODO.md) | 里程碑与任务清单（TASK-0001–0010）、待决策项 | 所有人 |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 分层、模块职责、数据流、API 契约 | 开发 |
| [`docs/DATA_SPEC.md`](docs/DATA_SPEC.md) | 坐标、ID、GeoJSON、SQLite schema、校验规则 | 开发、数据 |
| [`docs/EDITOR.md`](docs/EDITOR.md) | Web 编辑器与 QGIS 往返 | 开发 |
| [`docs/TESTING.md`](docs/TESTING.md) | 测试层级、边界用例、质量门禁 | 开发、评审 |
| [`docs/DEPENDENCIES.md`](docs/DEPENDENCIES.md) | 依赖登记表与升级流程 | 开发 |
| [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) | **环境与开源库清单（只列不装）** | 新人、人类 |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | D-001–D-021 决策记录 | 所有人 |
| [`docs/STATUS.md`](docs/STATUS.md) | 当前进度、已知问题、下一步 | 所有人 |
| [`DEVELOPMENT_PREP.md`](DEVELOPMENT_PREP.md) | v0.2 完整开发契约（**基线存档**，已拆分到上述文件） | 追溯 |

## 计划中的仓库结构

```text
MapCreator/
├─ AGENTS.md  CLAUDE.md  README.md  TODO.md
├─ docs/                 # 架构、数据、编辑器、测试、依赖、环境、决策、状态
├─ config/               # world.toml / kinds.toml / zoom_bands.toml / palette.toml
├─ schemas/              # JSON Schema（几何、标注、名称、各 kind 属性）
├─ world/                # 真源：world.json + geometry/*.geojson + annotations.sql
├─ assets/               # icons/ fonts/ ATTRIBUTION.md
├─ styles/               # base.maplibre.json / overrides.maplibre.json
├─ src/mapcreator/       # CLI、配置、db、build、server、qgis
├─ web/                  # Vite + 原生 JS 前端
├─ tests/                # unit / integration / e2e / golden / fixtures
├─ build/  dist/  artifacts/   # 产物（git 忽略）
├─ scripts/              # install-deps.ps1 / .sh（手动执行）
└─ pyproject.toml  package.json  biome.json  # uv.lock / package-lock.json 由安装脚本生成
```

## 快速开始

**第一步：安装依赖（手动执行、需要联网）**

```powershell
# PowerShell 7
pwsh -NoProfile -File scripts\install-deps.ps1 -DryRun   # 先预演
pwsh -NoProfile -File scripts\install-deps.ps1           # 真正安装

# 只有 Windows PowerShell 5.1 时
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\install-deps.ps1 -DryRun
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\install-deps.ps1
```

```bash
# WSL / Git Bash / macOS / Linux
bash scripts/install-deps.sh --dry-run
bash scripts/install-deps.sh
```

**第二步：跑命令**

```bash
uv sync --locked                  # 按 uv.lock 复现 Python 环境
uv run mapcreator doctor --json   # 环境自检（已可用）
uv run mapcreator build           # 尚未实现（TASK-0005）
uv run mapcreator serve           # 尚未实现（TASK-0006）
```

环境要求见 [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)（含已执行的安装/自检命令与镜像配置）。
安装脚本的开关与注意事项见 [`scripts/README.md`](scripts/README.md)。

## 开发方式

AI Agent 主导实现，人类负责决策、验收与方向调整。

1. 读 [`AGENTS.md`](AGENTS.md)（唯一入口）。
2. 从 [`TODO.md`](TODO.md) 取下一个任务。
3. 按任务的验收标准实现，跑 `check --full`，附证据。
4. 更新 [`docs/STATUS.md`](docs/STATUS.md)；决策写 [`docs/DECISIONS.md`](docs/DECISIONS.md)。

## 许可证

项目自身许可证待定（TBD）。第三方依赖、字体与图标的许可证逐项登记在 [`docs/DEPENDENCIES.md`](docs/DEPENDENCIES.md) 与 [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)。QGIS 仅作为**外部可选工具**使用，不链接、不随分发物捆绑。
