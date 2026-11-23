# civ-atlas UI / 编辑器移植方案（待确认）

> 目标：借鉴 [civ-atlas](https://github.com/guaner-334/civ-atlas) 的界面外壳与地图编辑交互，重做 MapCreator 的浏览/编辑体验。
> 不移植其世界生成与历史推演。视觉走**现代电子地图**风格（非手绘/羊皮纸）；**只做桌面端**。
> 编辑数据遵循现有规范（字段、ID、点标注不建几何）；落库分两步走——先做纯前端草稿 + 导出，再写临时测试库，最后才轮到正式库。
> 状态：**已确认（2026-11-19）**；任务号见 `TODO.md`：TASK-0013 只做**浏览外壳**（已实现，见 `STATUS.md`），编辑器归 TASK-0009。模块与存储约定已写入 `ARCHITECTURE.md` §3/§4/§6/§8/§10 与 `EDITOR.md`。
>
> **分支范围（2026-11-19 追加）**：`feat/civ-atlas-ui` 只做 **UI 界面**（浏览界面 + 编辑界面），**不写 TASK-0008 的搜索与只读 SQL**，也不写任何后端写端点。
> 因此本分支的编辑界面为**纯前端阶段**：草稿只存在浏览器内存，通过“导出 JSON”交付；`var/editor-test/` 临时库与 `serve --editable` 写端点都推迟到后续分支。
> **属性编辑的位置改到左栏**（不再用右侧详情面板承载编辑表单）——见 §3 与 §9 第 10 条，属于下一步待实现项，本文档已登记、尚未编码。

## 1. 范围

| 做 | 不做 |
|---|---|
| 三栏外壳：左侧图层/标注列表、地图全幅、右侧详情、底部状态 | 星球生成、板块/气候/侵蚀 |
| 图层分组、开关、图例、快捷键一览 | 民族/国家/战争/王朝推演、编年史、时间轴回放 |
| 点/线/面绘制、选择、拖拽、删除、顶点编辑 | 插件沙箱、AI、账号/云同步、作品墙 |
| 撤销/重做、键盘快捷键、命中容差、吸附 | 自研 Canvas 行星渲染、地球仪、投影切换、程序化地名 |
| 现代电子地图风格（扁平矢量、清晰层级、弱纹理） | 手绘/羊皮纸/水彩画风 |
| 桌面端（≥ 1280×720）完整可用 | 移动端、窄屏底部卡片、触屏手势 |
| 编辑数据先**纯前端草稿**、可导出 GeoJSON/annotations.json（后续再接临时库） | 写 `world/` 正式库、改现有只读接口契约 |
| 编辑界面（工具栏、绘制、属性编辑、撤销/重做） | TASK-0008 搜索 / 只读 SQL（不在本分支） |

临时库与写路径的补充约定（**属后续阶段，本分支不实现**）：

- 编辑器保存只允许走 Python 校验层（AGENTS §2.1）：新增 **dev-only** 写端点（`serve --editable` 时启用），默认写 `var/editor-test/annotations.db`，可 `--editor-db` 覆盖；`world/annotations.db` 永不被该端点打开。
- 空间/几何仍遵循现有规范：点标注不建几何（D-015），线/面 `geometry_id` 用 `geo.<kind>.<slug>`，名称只在 `annotation_name`，`min_zoom/max_zoom` 为 NULL 表示继承。
- 现有 `GET /api/health|world|data|annotations/{id}` 契约不变；写端点仅在开发模式挂载，生产 `serve` 不暴露。

配色与字号以 `config/palette.toml` 为唯一来源；`min_zoom/max_zoom` 为 NULL 时的继承语义不变；点标注仍不建几何（D-015）。

## 2. 参考实现结论

| 机制 | civ-atlas 位置 | 可借鉴点 |
|---|---|---|
| 全幅地图 + 浮层侧栏 | `src/ui/App.tsx:2914-3021`、`desktop.css:1-67` | 地图铺满窗口，面板用绝对定位浮在上面，`--side-w/--side-gap` 控制留白 |
| 左侧栏 | `src/ui/Sidebar.tsx:107-147` | 标题 + 搜索 + 详情插槽 + 内容区 + 收起态 |
| 右侧详情 | `src/ui/Inspector.tsx:83-158` | 宽屏进侧栏插槽（其窄屏抽屉仅作了解，本项目不做） |
| 面板零件 | `src/ui/panelParts.tsx:1-18` | PanelHead、Acts、Stats、SegBar、Foot 等可复用结构 |
| 主题 | `src/ui/theme.css:2-114` | `data-theme` + CSS 变量：`--ink/--panel/--accent/--map-mark`、圆角、阴影 |
| 图层弹层 | `src/ui/LayerPopover.tsx:268-407`、`mapLayers.ts:18-68` | 底图/叠加层分组、开关、图例 |
| 标记草稿状态机 | `src/ui/markStore.ts:63-193` | “放置→填表→校验→完成/取消”，选中变化自动丢弃草稿 |
| 标记命中 | `src/ui/MarkLayer.tsx:65-83`、`mapPick.ts:63-97` | 屏幕坐标容差、最小点选框 14px、取最近命中 |
| 图钉拖拽 | `src/ui/App.tsx:1907-1934` | `setPointerCapture`，移动即更新世界坐标 |
| 点击/悬停分派 | `src/ui/App.tsx:2071-2120` | 放置/编辑态优先，其次命中标记，最后空白 |
| 撤销/重做 | `src/ui/undo.ts:16-41` | 记录 `before/after`，整份 edits 替换，Toast 反馈 |
| 快捷键 | `src/ui/shortcuts.ts:94-118` | 按键位 `KeyboardEvent.code` 识别，输入框/弹窗内不响应 |
| 笔刷（可暂缓） | `src/ui/TerrainTools.tsx:469-582` | 半径/强度/连续采样；本轮不做地形笔刷 |

## 3. 目标界面

```text
┌─────────────────────────────────────────────────────────────┐
│ 顶部左：世界名 + 搜索占位      顶部右：图层 · 图例 · 导出 · ? │
├──────────────┬──────────────────────────────────────────────┤
│ 左侧栏 300px │                                              │
│ ▸ 图层       │                  MapLibre 地图               │
│   ├ 底图     │        （点/线/面 + DOM 标签 + 选中环）       │
│   ├ 水系     │                                              │
│   └ 点标注   │                                 ┌──────────┐ │
│ ▸ 标注列表   │                                 │ 右侧详情 │ │
│   城市 (2)   │                                 │ 320px    │ │
│   兴趣点 (6) │                                 └──────────┘ │
├──────────────┴──────────────────────────────────────────────┤
│ 状态栏：带 · zoom · 世界 · 标签数 · 选中 · 编辑工具           │
└─────────────────────────────────────────────────────────────┘
```

- 桌面端（≥ 1280×720）：左侧栏可收起（`Ctrl+\`），右侧详情复用现有 `#sidebar` 并重新排版。
- **浏览/编辑共用一套外壳**：浏览模式只渲染地图与只读面板，不挂载工具栏/绘制手柄/保存按钮；切换编辑模式后才加载编辑组件。
- **属性编辑在左栏（下一步实现项，尚未编码）**：
  - 编辑态左栏承载「属性」分节：`kind`、主名/多语言名、`rank`、`min_zoom/max_zoom`、`description`、`attrs`，以及保存/取消/删除按钮。
  - 右侧 `#sidebar` 在编辑态只保留**只读详情**（或不显示），不再承载编辑表单；浏览态完全不变。
  - 左栏在编辑态的顺序暂定：**工具 → 属性 → 图层 → 标注列表 → 世界信息**；“属性”放在工具栏正下方，便于画完立刻填表；最终顺序在实现时按可用性再确认。
  - 未选中/无草稿时，“属性”分节显示空态而不是隐藏，避免左栏高度跳动。
- **只做桌面端**：设计基准 1280×720 以上；不实现窄屏/底部卡片/触屏手势，窗口过窄时只保证不崩溃。
- 视觉：**现代电子地图**风格——扁平矢量、无纹理纸感、弱阴影、清晰的路网与点符号层级；颜色与字号全部取 `palette.toml`，面板用中性深/浅表面色，强调色只用于选中与工具态。

## 4. 组件落点

| 新文件 | 职责 | 来源参考 |
|---|---|---|
| `web/src/shell.js` | 组装左栏/顶栏/详情/状态栏，折叠与断点 | `App.tsx`、`Sidebar.tsx` |
| `web/src/panels.js` | PanelHead/Section/Row/Switch/Slider/ColorChip 等零件 | `panelParts.tsx` |
| `web/src/layers.js` | 按 `/api/world` 的 kind 与 style 图层生成分组、开关、图例 | `LayerPopover.tsx`、`mapLayers.ts` |
| `web/src/shortcuts.js` | `matchShortcut(KeyboardEvent)` + 快捷键表 | `shortcuts.ts` |
| `web/src/editor.js` | 工具状态机、Terra Draw 装配、指针分派、导出 | `markStore.ts`、`App.tsx:1907-2120` |
| `web/src/inspector.js` | 属性编辑分节（挂在**左栏**）、字段校验、保存/取消 | `Inspector.tsx`（仅参考字段分组，位置已改为左栏） |
| `web/src/history.js` | 编辑文档快照栈（撤销/重做，上限 100） | `undo.ts` |
| `web/src/pick.js` | 点选容差、最近命中、顶点手柄 | `MarkLayer.tsx`、`mapPick.ts` |

现有 [main.js](../web/src/main.js) 只保留启动与 URL 同步；[ui.js](../web/src/ui.js) 的详情渲染迁到 `panels.js` 的零件上重排；[labels.js](../web/src/labels.js) 增加“取当前带特征/标签框”接口给 `pick.js`。

## 5. 编辑交互设计

工具：`select | point | line | polygon | delete`（快捷键 `V/P/L/G/Delete`，`Esc` 取消当前草稿）。

状态机：

```text
idle ──选工具──▶ tool
tool=point   : 点击 → 生成点草稿 → 打开属性卡 → 完成/取消
tool=line    : 点击加点 → 双击/Enter 结束 → 简化 → 属性卡
tool=polygon : 点击加点 → 点回起点/双击结束 → 闭合 → 属性卡
select       : 点击命中 → 选中；拖动点 → 实时更新 lon/lat；Delete → 软删除草稿
任意          : Esc 回 idle；切换工具丢弃未完成草稿
```

- 指针：`pointerdown/move/up` + `setPointerCapture`；拖动超过 4px 才算拖拽，否则按点击处理。绘制时 `map.dragPan.disable()`，结束后恢复。
- 坐标：`map.unproject` 得到经纬度，统一 6 位小数；不跨 ±180°，超出 `bounds` 时拒绝并提示。
- 命中：优先 DOM 标签与顶点手柄（点选框最小 14px），其次 `queryRenderedFeatures` 查询 `annotation-*` 图层；多个命中取屏幕距离最近。
- 吸附：距已有顶点/线 ≤ 8px 时吸附；双击结束线/面；线做 Douglas-Peucker（容差按 zoom 带）。
- 撤销：每完成一次操作把“标注数组 + 几何集合”整体快照入栈；`Ctrl+Z / Ctrl+Shift+Z`；无后端参与。
- 属性卡字段：`kind`（下拉，来自 `/api/world`）、主名 + 各语种名、`rank`、`min_zoom/max_zoom`（留空=继承）、`description`、`attrs`（JSON 文本域）。
- **属性卡位置：左栏**（不是右侧 `#sidebar`）。选中标注或生成草稿后，左栏“属性”分节切换为编辑表单；保存前逐字段校验，错误就地显示在字段下方。
- 线/面：生成 `geometry_id = geo.<kind>.<slug>`，几何只进导出文件，不进标注对象。

## 6. 数据契约

### 6.1 本分支（纯前端草稿）

内存文档：

```js
{ annotations: [ { id, kind, lon, lat, rank, min_zoom, max_zoom, names: [...], description, attrs } ],
  geometries: { type: 'FeatureCollection', features: [...] } }
```

- 草稿只在浏览器内存中，刷新即丢失；不请求任何写接口，不碰 SQLite。
- 导出两个文件，格式与现有导入链路一致：
  - `annotations.json`：与 `tests/fixtures/mini-world/annotations.json` 同构（`id/kind/lon/lat/rank/names`），可由 `mapcreator annotations import` 导入。
  - `geometry.geojson`：RFC 7946，`properties` 只用白名单键，不写 `name`。
- 新 ID 规则：`anno.<kind>.<slug>`、`geo.<kind>.<slug>`；草稿期用 `new-<n>`，完成时按主名生成一次，之后不再改。
- 前端校验只用于交互提示；真正的校验在后续接写端点时由 Python 层执行（AGENTS §2.1）。

### 6.2 后续阶段（临时测试库，本分支不实现）

内存文档结构不变（同 6.1），新增的是落盘路径：

- 启动：`uv run mapcreator serve --editable --editor-db var/editor-test/annotations.db`；`--editable` 才挂写端点，默认 `serve` 保持只读。
- 写端点（dev-only）：沿用现有契约 `POST/PATCH/DELETE /api/annotations[/{id}]`；服务端做 kind/坐标/名称/zoom 校验并递增 `revision`。
- 持久化：临时库**跨重启保留、不清空**；首次启动若为空，从当前 `build/annotations.export.json` 播种。
- 几何：线/面写 `var/editor-test/geometry/*.geojson`，与临时库同生命周期，不写 `world/geometry/`。
- 数据隔离：服务端解析 `--editor-db` 后校验其**不得**指向 `world/annotations.db`；`var/` 加入 `.gitignore`。
- 读取：`--editable` 时详情从临时库读；普通 `serve` 仍读 `world/annotations.db`。
- 预览：编辑后用临时库重新构建（具体参数在实现时按 `build` 现有能力确定），不与正式 `build/` 混用。
- 导出：仍保留 `annotations.json` + `geometry.geojson` 两个文件，便于人工审阅或 `annotations import` 导入别的库。

## 7. 分期与验收

| 阶段 | 内容 | 验收 |
|---|---|---|
| P0 外壳（已完成） | `shell.js/panels.js/layers.js/shortcuts.js`；左栏、顶栏、详情重排、状态栏；现代电子地图视觉 | 地图全幅、左栏可收起、图层可开关、无控制台错误；1280×720 下布局不溢出；`npm run check` + `build`；截图 |
| P1a 编辑界面（**本分支**，纯前端） | Terra Draw 接入（官方 MapLibre 适配器）、点/线/面、选择/拖拽/删除、撤销/重做、**左栏属性编辑**、导出 JSON | 能画出 1 点/1 线/1 面并在左栏填完属性；撤销/重做覆盖绘制与属性修改；导出 JSON 可被 `annotations import` 接受；浏览模式仍无编辑控件；1280×720 截图 |
| P1b 编辑落库（后续分支） | dev-only 写端点 + `var/editor-test/` 临时库 | 保存后重启 `serve --editable` 数据仍在；`world/annotations.db` 修改时间不变 |
| P2 打磨 | 图例、快捷键弹窗、标签与顶点手柄细节、错误/空态 | 桌面端 1280/1440/1920 三档截图无溢出；拖动 60fps、无标签抖动；临时库与正式库切换明确可见 |

任务已写入 TODO：

- `TASK-0013` 浏览外壳（P0，纯前端），Deps：TASK-0007 —— **已完成**
- `TASK-0009` 编辑器：阶段 A（P1a 前端编辑界面，本分支）+ 阶段 B（P1b 落库）；阶段 A 不依赖 TASK-0008，阶段 B 按原顺序排在 TASK-0008 之后
- P0 收尾（图例、快捷键弹窗、空态）随 TASK-0013；P1a 属本分支，P1b/P2 属后续

## 8. 许可与合规

- civ-atlas 为 **AGPL-3.0-only**。若复制其代码/样式片段，本仓库作为衍生作品需按 AGPL 分发，并保留版权声明与许可文本；联网提供服务时需提供对应源码。
- 本方案默认“参考交互、重写实现”，不直接复制源码；若后续决定复制，需在 `LICENSE`/`NOTICE` 与 `docs/DECISIONS.md` 中记录。
- 不新增别的前端依赖：继续用原生 ES 模块 + MapLibre + 已登记的 `terra-draw@1.40`。
- **新增（已安装并接入）**：`terra-draw-maplibre-gl-adapter@1.5.0`（Terra Draw 官方 MapLibre 适配器；原拟包名在 npm 不存在），已登记 `DEPENDENCIES.md`。

## 9. 已确认决策

1. **视觉**：现代电子地图风格（扁平矢量、弱纹理），不使用手绘/羊皮纸；颜色字号取 `palette.toml`。
2. **平台**：只做桌面端（基准 1280×720），不做移动端与触屏手势。
3. **共用外壳**：浏览与编辑共用一套 UI；浏览模式只渲染地图与只读面板，不挂载工具组件。
4. **左栏顺序**：浏览态 图层 → 标注列表 → 世界信息；编辑态在图层之上插入 工具 与 属性（见第 10 条）。
5. **临时库**：`var/editor-test/annotations.db` 跨重启保留、不清空；首次为空时从当前构建播种。
6. **几何存放**：线/面写 `var/editor-test/geometry/`，不写 `world/geometry/`。
7. **属性卡**：一次做全（kind、主名/多语言名、rank、min/max zoom、description、attrs）。
8. **正式库**：本轮不写 `world/annotations.db`；正式写入留给后续阶段。
9. **分支范围**（2026-11-19 追加）：`feat/civ-atlas-ui` 只做 UI（浏览 + 编辑），TASK-0008 搜索/只读 SQL 不在本分支；编辑界面阶段数据**只在浏览器内存**，用“导出 JSON”交付，不写后端、不建临时库。
10. **属性编辑位置**（2026-11-23 已实现）：节点属性从右侧详情面板**移到左栏**的“属性”分节；右侧详情在编辑态退化为只读。左栏编辑态顺序已确认为 工具 → 属性 → 图层 → 标注列表 → 世界信息。
11. **绘制适配器**（2026-11-23 更正包名并接入）：使用 Terra Draw 官方 MapLibre 适配器 `terra-draw-maplibre-gl-adapter@1.5.0`，不自研适配层。

遗留风险：AGPL 合规取决于是否复制源码（默认重写）；Terra Draw 的撤销/顶点 API 需按锁定版本核对；临时库预览构建的具体命令在 TASK-0009 实现时确认。
