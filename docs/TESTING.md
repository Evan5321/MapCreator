# 测试与质量门禁（TESTING）

> 目标 ≤ 150 行。命令约定见 [`ARCHITECTURE.md`](ARCHITECTURE.md)，数据结构见 [`DATA_SPEC.md`](DATA_SPEC.md)。

## 1. 层级

| 层级 | 内容 | 工具 | 目录 |
|---|---|---|---|
| 单元 | schema、ID、zoom 推导、样式生成、DB CRUD、搜索 | pytest | `tests/unit/` |
| 集成 | mini-world 构建、导入导出、dump/restore、API | pytest + httpx | `tests/integration/` |
| Golden | 规范化 style、manifest 计数、标注导出、SQL dump | pytest | `tests/golden/` |
| E2E | 加载、缩放、标注出现、搜索、编辑、保存 | pytest + Playwright | `tests/e2e/` |
| 视觉 | 固定视口/URL 截图 | Playwright | `artifacts/` |
| 性能 | 构建时间、加载、标注数、内存 | Playwright metrics + 计时 | `artifacts/perf.json` |

夹具统一基于 `tests/fixtures/mini-world/`（1 大陆、1 海、2 河、1 山脉、2 城、5 POI、1 地铁线），不要依赖真实世界数据。

## 2. 必须覆盖的边界用例

- **搜索**：1 字符、2 字符（`上海`）、3 字符、纯英文、别名、含空格/标点、跨语种命中同一标注。
- **多语言**：只有 `zh`；`zh+en`；第三语种；`is_primary` 缺失/重复被拒。
- **点/线标注**：点标注带 `geometry_id` 被拒；线标注关联面几何被拒。
- **缩放带交界**：`z3→z4`、`z6→z7`、`z15→z16` 不重复、不闪断、计数与 manifest 一致。
- **zoom 回填**：`min/max_zoom` 为 NULL 时用 kind 默认值，且**不写回库**。
- **引用完整性**：删除被引用几何 → 409；`--cascade` → 软删且可恢复；`parent_id` 成环被拒。
- **并发**：陈旧 `revision` → 409，无脏写。
- **dump 往返**：逻辑表字节级一致；restore 后 FTS/RTree 重建，搜索结果一致。
- **确定性**：同输入重建两次，`build/` 除字体/图标二进制外字节一致（二进制记哈希）。

## 3. Golden 规则

- golden 文件存**规范化后**输出：稳定排序、6 位小数、固定缩进、无时间戳。
- 变化必须解释：更新 golden 时在 PR/报告中写明"为什么变"。
- 字体/图标二进制不入 golden，只存 SHA-256。
- style golden 用 style-spec 校验后的规范化 JSON。

## 4. E2E 与视觉

- E2E 除截图外必须做 DOM/JS 断言，测试模式暴露 `window.__app`：
  `ready`、`zoom`、`center`、`visibleLabelCount`、`selectedId`、`band`。
- 截图存 `artifacts/<task>/<case>.png`，AI 必须**读取并检查**：
  - 地图是否加载（不是空白/灰屏）；
  - 各带标注是否按规则出现/消失；
  - 是否有明显重叠、裁切、空洞；
  - 中文是否正常（无方块字）；
  - `#lang=` 多语言叠加是否正确。
- WebGL 无头截图跨 GPU/OS 可能像素差异：**初期不做像素断言**，稳定后再加小容差对比。

## 5. 性能测量

`check --full` 输出 `artifacts/perf.json`，至少含：全量构建耗时、增量构建耗时、初始载荷（gzip）、每带标注数、可交互时间、FPS 采样、内存峰值。

预算（超标需 ADR + 测量数据）：

| 指标 | 预算 |
|---|---|
| 源要素 | ≤ 50k 几何 + ≤ 20k 标注 |
| 全量构建 | ≤ 20 s |
| 增量构建 | ≤ 3 s |
| 初始载荷（gzip） | ≤ 8 MB |
| 每带标注 | ≤ 3000 |
| 可交互 | ≤ 2.5 s（本地） |
| 缩放/平移 | ≥ 55 fps |
| 搜索 p95 | ≤ 100 ms |
| 浏览器内存 | ≤ 300 MB |

## 6. 门禁（任一失败禁止标完成）

- `uv run mapcreator check --full --json` 非零退出。
- 数据校验有错误；警告未记录。
- UI 变更无截图证据，或截图未经查看。
- 新依赖未登记 `DEPENDENCIES.md`。
- schema/DB 变更无迁移或文档。
- 构建不可重复（golden 变化未解释）。
- 性能超预算且无 ADR。

## 7. 命令

```bash
uv run pytest tests/unit -q
uv run pytest tests/integration -q
uv run pytest tests/e2e -q                     # 需要 Playwright 浏览器
uv run mapcreator validate --json
uv run mapcreator check --full --json
```

M0 阶段若 `check` 尚未实现，用 ruff + mypy + pytest 的组合并在报告中说明等价关系。

## 8. CI（可选）

本地 `check --full` 是硬要求；GitHub Actions 只作补充。CI 不跑需要 QGIS/Docker 的步骤，用 `doctor` 标记跳过；截图作为 artifact 上传供评审。
