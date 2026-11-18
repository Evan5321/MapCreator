# 开发环境与开源库清单（ENVIRONMENT）

> **这是一份清单，不是安装脚本。** 编写时**没有执行**任何安装、克隆、下载或联网校验；版本号也**没有**预先锁定——真正的版本以 TASK-0001 生成的 `uv.lock` / `package-lock.json` 为准。
> 依赖登记规则与升级流程见 [`DEPENDENCIES.md`](DEPENDENCIES.md)；技术选型理由见 [`DECISIONS.md`](DECISIONS.md)。

阅读方式：

- 第 1 节是**机器上必须存在**的东西（由人类安装，不由 Agent 安装）。
- 第 2–5 节是**项目依赖**，按语言/类型分组，附 GitHub 地址与许可证。
- 第 6 节是将来会用到但**现在不执行**的命令，仅供 TASK-0001 使用。
- 许可证一列凡写"以仓库 LICENSE 为准"的，TASK-0001 必须逐项核对后改为确定值。

## 1. 系统前置条件

| 依赖 | 必需 | 版本要求 | 用途 | 备注 |
|---|---|---|---|---|
| Windows | 是 | 11（10 亦应可用） | 目标平台 | 路径/编码按 `DATA_SPEC` 规则处理 |
| Python | 是 | 3.12+ | 后端、构建、CLI、测试 | 需含 stdlib `sqlite3`（FTS5 + RTree + trigram） |
| [uv](https://github.com/astral-sh/uv) | 是 | 最新稳定 | Python 环境与锁文件 | `uv.lock` 必须提交 |
| [Node.js](https://github.com/nodejs/node) | 是 | 20 LTS+ | 前端构建、样式校验 | 运行时不依赖 Node |
| npm | 是 | 随 Node | 前端依赖 | 提交 `package-lock.json` |
| [Git](https://git-scm.com/) | 是 | 任意较新版本 | 版本管理 | `core.autocrlf` 配合 `.gitattributes` |
| 浏览器 | 是 | Edge/Chrome/Firefox 现代版 | WebGL2 渲染与 Playwright | 无 WebGL2 则无法渲染 |
| [QGIS](https://github.com/qgis/QGIS) | 否 | 3.34+ | 批量绘制、拓扑检查、比例尺预览 | GPL；**仅外部工具**，不链接不捆绑 |
| Docker 或 WSL | 否 | — | 后续 tippecanoe 切片 | MVP 不需要 |
| [tippecanoe](https://github.com/felt/tippecanoe) | 否 | — | 后续可选瓦片 | 原生 Windows 支持有限 |
| Playwright 浏览器 | 是（E2E 时） | 与 Python 包匹配 | 无头截图 | `playwright install chromium` 需联网，**未经批准不执行** |

SQLite 能力要求（Python 自带 `sqlite3` 即可，不额外安装）：`ENABLE_FTS5`、`ENABLE_RTREE`、`trigram` tokenizer（SQLite ≥ 3.34）。由 `mapcreator doctor` 检查。

## 2. Python 依赖

| 库 | 用途 | GitHub | 许可证 | 形态 |
|---|---|---|---|---|
| `uv` | 环境/依赖/锁文件 | https://github.com/astral-sh/uv | MIT 或 Apache-2.0（双许可，以仓库为准） | 独立二进制 |
| `typer` | CLI 入口 | https://github.com/fastapi/typer | MIT | 纯 Python |
| `fastapi` | 本地 HTTP API | https://github.com/fastapi/fastapi | MIT | 纯 Python |
| `uvicorn` | ASGI 服务器 | https://github.com/encode/uvicorn | BSD-3-Clause | 纯 Python（`uvloop` 非 Windows） |
| `pydantic` | 数据模型/校验 | https://github.com/pydantic/pydantic | MIT | 有预编译 wheel |
| `pydantic-settings` | 配置加载 | https://github.com/pydantic/pydantic-settings | MIT | 纯 Python |
| `geojson-pydantic` | GeoJSON 模型 | https://github.com/developmentseed/geojson-pydantic | MIT（以仓库为准） | 纯 Python |
| `shapely` | 几何有效性/简化/运算 | https://github.com/shapely/shapely | BSD-3-Clause | 有 wheel（含 GEOS） |
| `watchfiles` | 开发监听 | https://github.com/samuelcolvin/watchfiles | MIT | 有 wheel（Rust 扩展） |
| `pytest` | 测试主框架 | https://github.com/pytest-dev/pytest | MIT | 纯 Python |
| `httpx` | API 集成测试客户端 | https://github.com/encode/httpx | BSD-3-Clause | 纯 Python |
| `playwright` | E2E/截图（Python 驱动） | https://github.com/microsoft/playwright-python | Apache-2.0 | 有 wheel + 需下载浏览器 |
| `ruff` | 格式 + lint | https://github.com/astral-sh/ruff | MIT | 独立二进制（有 wheel） |
| `mypy` | 静态类型检查 | https://github.com/python/mypy | MIT | 纯 Python |

原则：优先**纯 Python 或有预编译 wheel**的库；避免本机 C++ 编译链。若某库在 Windows 需要编译，必须在 `DEPENDENCIES.md` 注明并说明替代方案。

## 3. 前端 / 构建依赖

| 包 | 用途 | GitHub | 许可证 | 备注 |
|---|---|---|---|---|
| `vite` | 开发服务器与打包 | https://github.com/vitejs/vite | MIT | 仅构建期 |
| `maplibre-gl` | 地图渲染引擎 | https://github.com/maplibre/maplibre-gl-js | BSD-3-Clause | 运行时核心 |
| `terra-draw` | 点/线/面绘制与编辑 | https://github.com/JamesLMilner/terra-draw | MIT | 含 MapLibre adapter |
| `@json-editor/json-editor` | 由 JSON Schema 生成属性表单 | https://github.com/json-editor/json-editor | MIT（以仓库为准） | 避免手写表单 |
| `@maplibre/maplibre-gl-style-spec` | 样式 JSON 校验 | https://github.com/maplibre/maplibre-gl-style-spec | 以仓库 LICENSE 为准（ISC 系） | 构建期与测试期使用 |
| `@biomejs/biome` | JS 格式 + lint | https://github.com/biomejs/biome | MIT | 单一工具替代 ESLint+Prettier |

不引入前端框架（React/Vue/TS）——见 D-008。

## 4. 资产（字体与图标）

| 资产 | 用途 | 来源 | 许可证 | 备注 |
|---|---|---|---|---|
| Noto Sans glyph PBF | 拉丁字形 | https://github.com/openmaptiles/fonts | 以仓库 LICENSE 为准（Noto 为 OFL） | 避免 Windows 上编译字体工具 |
| Noto 字体源 | 字形来源与再生成 | https://github.com/notofonts/noto-fonts | OFL-1.1 | 记录版本与哈希 |
| Maki 图标 | POI 图标 | https://github.com/mapbox/maki | 以仓库 LICENSE 为准（CC0 系） | 栅格化为 PNG |
| Temaki 图标 | 补充图标 | https://github.com/rapideditor/temaki | 以仓库 LICENSE 为准 | 需单独核对 |
| CJK 字形 | 中日韩文字 | 系统字体（`localIdeographFontFamily`） | 随系统 | **不生成** CJK glyph PBF |

所有资产必须写入 `assets/ATTRIBUTION.md`：来源、版本、许可证、哈希。字体/图标二进制不入 golden，只存 SHA-256。

## 5. 外部可选工具

| 工具 | 用途 | 地址 | 许可证 | 使用方式 |
|---|---|---|---|---|
| QGIS | 批量/拓扑编辑 | https://github.com/qgis/QGIS | GPL-2.0+ | 独立进程，通过 GeoJSON 文件往返 |
| Maputnik | 样式可视化调参 | https://github.com/maplibre/maputnik | MIT | 浏览器中打开，仅调 base/overrides |
| tippecanoe | 生成 MBTiles | https://github.com/felt/tippecanoe | 以仓库 LICENSE 为准（BSD 系） | Docker/WSL，MVP 不用 |
| PMTiles | 单文件瓦片格式与工具 | https://github.com/protomaps/PMTiles | 以仓库 LICENSE 为准（BSD 系） | 性能优化阶段再评估 |
| SQLite 源码/CLI | 参考与人工排查 | https://github.com/sqlite/sqlite | Public Domain | 项目只依赖 stdlib `sqlite3` |

以上全部**不写入** Python/Node 依赖；由 `mapcreator doctor` 检测是否可用，不要求存在。

## 6. 已执行的命令（2026-11-18，Windows + PowerShell）

以下命令已经跑过，产物为 `uv.lock`、`package-lock.json`、`.venv/`、`node_modules/`。
Python 依赖走清华 TUNA 镜像（配置在 `pyproject.toml` 的 `[tool.uv.index]`），npm 走 `npmmirror`（`.npmrc`）。

```bash
# Python 环境（生成 uv.lock）
uv sync

# 前端依赖（生成 package-lock.json）
npm ci

# E2E 浏览器（约数百 MB，首次需要联网）
PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright uv run playwright install chromium

# 环境自检
uv run mapcreator doctor --json
```

## 7. 网络与离线

- 首次安装需要访问 PyPI、npm registry，以及 Playwright 的浏览器 CDN。
- 字体 PBF、图标集属于**手动下载**资产，应在仓库中固定版本并记录哈希（避免"今天拉的和昨天不一样"）。
- 日常开发（构建、校验、测试单测/集成）**不需要**网络。
- 任何联网动作（安装、克隆、下载）都需要人类批准；Agent 不得自行发起。

## 8. 版本策略

- 不在文档里写死具体版本号；写死在 `uv.lock` / `package-lock.json`。
- 升级依赖必须单独任务，附 `check --full` 结果与 `DEPENDENCIES.md` 更新。
- 不追求"最新"，追求"锁定 + 可复现 + Windows 无编译"。

## 9. 校验方式（TASK-0002 之后）

```bash
uv run mapcreator doctor --json
```

应输出：Python/uv/Node/npm 版本、SQLite 的 FTS5/RTree/trigram 能力、Playwright 浏览器是否就绪、可选工具（QGIS/Docker/tippecanoe）是否存在，以及每项的修复建议。缺失必需项时退出码为 3。
