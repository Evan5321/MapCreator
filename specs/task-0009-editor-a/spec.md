# TASK-0009 阶段 A — 纯前端编辑器（实施规格）

> 分支：`feat/civ-atlas-ui`。范围：只做编辑界面；草稿仅在浏览器内存，通过导出 JSON 交付。
> 依据：[`docs/EDITOR.md`](../../docs/EDITOR.md)、[`docs/CIV_ATLAS_UI_PORT.md`](../../docs/CIV_ATLAS_UI_PORT.md)、[`docs/DECISIONS.md`](../../docs/DECISIONS.md) ADR-024、[`TODO.md`](../../TODO.md) TASK-0009。

## 1. 已核实的现状与结论

- `terra-draw@1.40.0` 已安装；官方 MapLibre 适配器的**真实包名是 `terra-draw-maplibre-gl-adapter`**（文档里写的 `terra-draw-maplibre-gl` 不存在，npm 404）。
- 已安装 `terra-draw-maplibre-gl-adapter@1.5.0`（peer：`terra-draw ^1.0.0`、`maplibre-gl >=4`），`package.json` / `package-lock.json` / `DEPENDENCIES.md` 均已同步为正确包名。
- Terra Draw 1.40 已核实 API：`new TerraDraw({ adapter, modes })`、`start/stop`、`getSnapshot/getSnapshotFeature`、`addFeatures/removeFeatures`、`setMode`、`selectFeature/deselectFeature`、`updateFeatureProperties/updateFeatureGeometry`、`on('finish'|'change'|'select'|'deselect')`；`change` 的 `type` 为 `create|update|delete|styling`。适配器构造：`new TerraDrawMapLibreGLAdapter({ map })`。
- 标注模型（`src/mapcreator/models.py`）：`id` 匹配 `anno.<kind>.<slug>`；若 `geometry_id` 非空则 `label_mode` 不能是 `point`；`names` 非空时必须**恰好一个** `is_primary`；`rank` 1–5；`min_zoom <= max_zoom`。
- 几何模型：`id` 匹配 `geo.<kind>.<slug>`；`properties.kind` 必填；禁止 `name/rank/min_zoom/max_zoom/description/layer`。
- 导入链路：`annotations import` 通过 `load_export` 走 Pydantic 校验（接受 `{"annotations":[...]}`）。
- 浏览外壳（shell/panels/layers/labels/shortcuts）已就绪；`editor.js` 目前是抛错的骨架。

## 2. 目标行为（阶段 A 验收映射）

| 验收项 | 实现 |
|---|---|
| 浏览模式无编辑控件 | 工具条/属性分节只在 `enable()` 时插入 `#leftbar-body` 顶部；`disable()` 移除；顶栏仅有「进入编辑」按钮 |
| 点/线/面各画一条 | Terra Draw `point` / `linestring` / `polygon`（另含 `rectangle`）模式，点击/双击结束 |
| 拖拽锚点、顶点编辑、吸附 | select 模式 flags：`draggable`、`coordinates.{draggable,deletable,midpoints,snappable}`，`pointerDistance: 8` |
| 左栏属性编辑 | 新增 `inspector.js`，字段：kind、多语言名（主名单选）、rank、min/max zoom、description、attrs(JSON)；错误就地显示；右侧详情仍只读 |
| 撤销/重做覆盖绘制/拖拽/属性 | 新增 `history.js`：整份文档快照（drafts + Terra 要素），上限 100；`Ctrl+Z` / `Ctrl+Shift+Z` |
| 导出可被 `annotations import` 接受 | 「导出」生成 `annotations.json` + `geometry.geojson`；点标注 `label_mode=point` 且无 `geometry_id`；线/面标注 `label_mode=line` 并带 `geometry_id` |
| 1280×720 无溢出 | 左栏分区滚动、属性表单自适应；截图证据 |
| `npm run check` / `npm run build` | 门禁 |

## 3. 文件级改动

### 3.1 新增 `web/src/history.js`
- `createHistory({ limit = 100 })` → `{ push(snapshot, label), undo(), redo(), canUndo(), canRedo(), clear(), reset(snapshot), depth() }`。
- 快照结构由调用方给出；`push` 与栈顶完全相同（`JSON.stringify`）时忽略。
- 撤销栈在 push 前把当前状态作为基线；重做栈在 undo 时记录。

### 3.2 新增 `web/src/inspector.js`
- `createInspector({ world, onChange })` → `{ element, open(draft), close(), setDisabled(bool), destroy() }`。
- 表单：`kind`（select，来自 `world.kinds`）、名称行（lang/name/主名 radio/删除）、`添加语种`、`rank`（1–5）、`min_zoom`/`max_zoom`（留空=继承）、`description`、`attrs`（textarea，JSON）、按钮「保存」「取消」「删除」。
- 前端校验（显示在字段下方）：ID 段合法、至少一个名称、恰好一个主名、rank 1–5、zoom 区间、attrs 为 JSON 对象、lang 形如 BCP47。
- 保存时回调 `onChange({ action: 'save', draft })`；取消/删除同理。

### 3.3 重写 `web/src/editor.js`
- `createEditor({ map, world, onStatus, onSelection })` → `{ enable, disable, isEnabled, setTool, getTool, selectAnnotation, addExisting, exportPayload, undo, redo, canUndo, canRedo, destroy, probe }`。
- Terra Draw 装配（适配器 + select/point/linestring/polygon/rectangle 模式）；`enable()` 时 `start()` 并把「工具」「属性」分节插入左栏顶部；`disable()` 时 `stop()` 并移除分节。
- 工具：选择 `V`、点 `P`、线 `L`、面 `G`、矩形 `R`、删除 `Delete`；`Esc` 取消草稿。
- `finish` 事件 → 建立草稿记录（默认 kind=首个 kind、默认语种主名占位），打开属性分节，切到 select 并选中。
- 文档记录：
  ```js
  { key, terraId, annotationId, geometryId, kind, names[], rank, min_zoom, max_zoom,
    description, attrs, labelMode, origin: 'draft'|'existing', lon, lat }
  ```
- 历史：`finish`/`change`(非 styling)/属性保存/删除 → 250ms 防抖后 `push()`；撤销恢复 drafts + Terra 快照（`clear()` + `addFeatures()`，恢复期间抑制事件）。
- 导出：`annotations.json`（跳过未保存或非法的草稿，给出计数）与 `geometry.geojson`（仅线/面，`properties={kind}`，`id=geometryId`）；通过 Blob 下载。
- ID：`slug = 主名转小写、空白→_、仅保留 [a-z0-9_]`；为空或冲突时用 `fig_<n>` 后缀；`anno.<kind>.<slug>` / `geo.<kind>.<slug>`。

### 3.4 `web/src/shell.js`
- 增加 `setMode(mode)`：切换 `#topbar-subtitle` 文案（`浏览模式 · 只读` / `编辑模式 · 草稿仅存内存`）与 `document.body` 的 `is-editing` 类；返回 `{ ... }` 中追加。
- 左栏顺序天然满足：编辑器分节插入在图层分节之前。

### 3.5 `web/index.html`
- 顶栏新增 `#btn-mode`（进入/退出编辑）、`#btn-export`（默认 `hidden`）。

### 3.6 `web/src/main.js`
- 装配 `createEditor`；`#btn-mode` 切模式并调用 `shell.setMode`；编辑态显示导出按钮。
- 编辑态禁用地图空白点击选中标注（避免与绘制冲突）；列表行仍可选中。
- 选中 id：先查编辑器草稿 → 有则打开属性分节；否则走只读详情（`getAnnotation`）。
- `Escape`：优先取消编辑器草稿/关闭属性，其次清选中。
- `window.__app` 追加 `mode`、`tool`、`draftCount` 探针。
- 编辑态给 `document.body` 加 `is-editing`，DOM 标签在编辑态 `pointer-events: none`。

### 3.7 `web/src/style.css`
- 工具按钮网格、激活态、表单字段/错误/操作区、编辑态标签穿透、1280×720 内滚动。

### 3.8 文档
- `docs/DEPENDENCIES.md`：包名改为 `terra-draw-maplibre-gl-adapter`、版本 `1.5.0`、状态「已安装并接入」。
- 完成后勾选 `TODO.md` TASK-0009 阶段 A、更新 `docs/STATUS.md`（截图路径与命令输出）。

## 4. 明确不做

- 不实现后端写端点、临时库、`serve --editable`（阶段 B/C）。
- 不实现 TASK-0008 搜索。
- 不自研 Terra Draw 适配层；不手写地图图层绘制草稿。
- 不引入 React 或新框架；`@json-editor/json-editor` 仍不使用。

## 5. 验证步骤（含证据）

1. `npm run check` → 0 问题。
2. `npm run build` → 产出 `web/dist`。
3. 构建演示世界（已存在则跳过）：`uv run mapcreator build --root worlds/metro --json`。
4. 启动 `uv run mapcreator serve --port 8767`（后台，`$env:TEMP/$env:TMP=var/tmp`）。
5. Playwright（脚本放 `var/tmp/`，截图放 `var/screenshots/`）：
   - 1280×720 下浏览模式断言无 `#tool-grid`、无 `#inspector`、无导出按钮；
   - 点「进入编辑」→ 断言工具条与属性分节出现、左栏顺序为 工具/属性/图层/标注列表/世界信息；
   - 依次绘制点、线、面；在属性分节填 kind/主名/rank/简介/attrs 并保存；
   - 拖动一条线/面顶点与拽动点，`Ctrl+Z` / `Ctrl+Shift+Z` 验证撤销重做；
   - 下载导出文件，断言 `annotations.json` 与 `geometry.geojson` 的结构；
   - 全程收集 `console.error`，要求为空；输出截图。
6. 用 Python 复用 `load_export` 校验导出的 `annotations.json`（不写库，规避 Agent 无法创建 SQLite 的限制），并记录说明。
7. 完成后更新 `TODO.md` / `docs/STATUS.md` / `docs/DEPENDENCIES.md`。

## 6. 需要人类确认的点

1. **依赖名更正**：文档里的 `terra-draw-maplibre-gl` 在 npm 不存在，已改为官方包 `terra-draw-maplibre-gl-adapter@1.5.0` 并安装；请确认接受这一更正。
2. 阶段 A 中「选中已有标注」的行为：读取服务端详情后作为**可编辑草稿副本**进入左栏属性表单（草稿与既有标注同 ID）；导出会包含该副本。若不希望修改既有标注，可改为只读。
