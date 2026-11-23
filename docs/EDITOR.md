# 编辑器（EDITOR）

> 目标 ≤ 150 行。字段规则见 [`DATA_SPEC.md`](DATA_SPEC.md)，端点见 [`ARCHITECTURE.md`](ARCHITECTURE.md) §6。
> 一句话：**Web 编辑器管日常标注与线面几何，QGIS 管批量与拓扑，自研桌面编辑器不做。**

## 1. 策略

| 方案 | 用途 | 决策 |
|---|---|---|
| Web 编辑器（Terra Draw） | 日常点/线/面 + 标注编辑 | MVP 必做 |
| 浏览与编辑共用外壳 | 一套 UI，两种模式 | 浏览模式只渲染地图与只读面板，不挂载工具组件 |
| QGIS | 批量绘制、拓扑检查、海岸线/边界精修 | 可选，不装也能完成 MVP |
| 自研桌面编辑器 | 产品化 | 暂不做；需要时先 ADR |

界面约束：

- **只做桌面端**（基准 1280×720）；不做移动端与触屏手势。
- 视觉为**现代电子地图**（扁平矢量、弱纹理、清晰层级），不使用手绘/羊皮纸风格。
- 左栏顺序：浏览态 图层 → 标注列表 → 世界信息；**编辑态 工具 → 属性 → 图层 → 标注列表 → 世界信息**（属性编辑在左栏，不用右侧面板）。
- 浏览模式不出现工具栏、绘制手柄、保存按钮；切换到编辑模式才挂载。
- **分阶段**：本分支（`feat/civ-atlas-ui`）只做编辑界面，草稿仅存浏览器内存并支持导出 JSON；写库端点与临时库属后续阶段。

阶段划分（与 `TODO.md` 的 TASK-0009 对应）：

| 阶段 | 内容 | 存储 |
|---|---|---|
| A（本分支） | 工具、绘制、选择/拖拽/顶点、撤销/重做、左栏属性编辑 | 浏览器内存 + 导出 `annotations.json` / `geometry.geojson` |
| B（后续） | dev-only 写端点、`serve --editable` | `var/editor-test/annotations.db` + `var/editor-test/geometry/` |
| C（后续） | 正式库写入、冲突处理 | `world/annotations.db` |

## 2. 工具与数据的映射

这是最容易搞错的一处，先记住（D-015）：

| 工具 | 写入什么 | 说明 |
|---|---|---|
| 点 | **只写标注**（`anno.*`，含 `lon/lat`） | 不产生 GeoJSON 要素；`geometry_id` 为 NULL |
| 线 | 写几何（`geo.*`，`rivers/roads/transit.geojson`） | 可选再挂一个 `label_mode=line` 的标注 |
| 多边形 / 矩形 | 写几何（`geo.*`） | 可选挂一个 `label_mode=point` 的标注（锚点在面内） |
| 顶点编辑 | 改几何 | 归属文件由 `kind` 决定，不允许跨文件搬要素 |

## 3. Web 编辑器功能

- 工具：选择、点、线、多边形、矩形、自由绘制；顶点拖拽、增删顶点。
- 交互：拖动 > 4px 才算拖拽；点选框最小 14px；距已有顶点/线 ≤ 8px 吸附；`Esc` 取消、双击结束线/面。
- 绘制引擎：Terra Draw + **官方 MapLibre 适配器** `terra-draw-maplibre-gl-adapter@1.5.0`（已安装并接入；原拟包名在 npm 不存在），不自研适配层。
- 撤销/重做：会话内快照栈（上限 100）；用 Terra Draw 自带能力时**先核对锁定版本 API**，不凭记忆写。
- 属性表单**一次做全**：`kind`、主名/多语言名、`rank`、`min_zoom/max_zoom`（留空=继承）、`description`、`attrs`。
- **属性表单在左栏**：作为左栏“属性”分节，放在工具栏下方；选中标注或生成草稿即切换为编辑表单，保存/取消/删除按钮同区；右侧 `#sidebar` 在编辑态只保留只读详情。
- 名称编辑：至少一个主名（`is_primary`）；可加任意语种与别名；不能删到零个。
- 保存（阶段 A）：只把这些编辑结果合成导出文件（`annotations.json` + `geometry.geojson`），不发请求。
- 保存（阶段 B 起）：一次提交一个或多个要素 → 服务端逐条校验 → 返回逐要素错误（部分成功要明确列出）。
- 软删除 + 恢复；删除需二次确认。
- 锚点拖动：线/面标注的 `lon/lat` 可拖动优化位置，不影响几何。

## 4. 保存协议

阶段 A（本分支）：**不落库**。编辑器只维护内存草稿，提供“导出 JSON”；导出文件格式与下面链路一致，后续可直接 `mapcreator annotations import`。

阶段 B 起（TASK-0009 后续）再写**临时测试库**，不碰 `world/`：

- 启动：`uv run mapcreator serve --editable --editor-db var/editor-test/annotations.db`；未加 `--editable` 时不挂写端点。
- 临时库**跨重启保留**，不清空；首次启动若库为空，从当前 `build/annotations.export.json` 播种。
- 线/面几何写 `var/editor-test/geometry/*.geojson`，与临时库同生命周期；不写 `world/geometry/`。
- 服务端解析路径后必须校验其不等于 `world/annotations.db`；`var/` 不提交（见 `.gitignore`）。
- 普通 `serve` 仍只读 `world/annotations.db`；两库切换由启动参数决定，界面显示当前所处模式。
- 正式库写入（TASK-0009）沿用同一协议，只切换目标库。

```text
PATCH /api/annotations/anno.city.silverrun
{ "revision": 7, "rank": 2, "names": [{"lang":"zh","name":"银流城","is_primary":true},
                                      {"lang":"en","name":"Silverrun","is_primary":false}],
  "attrs": {"population": 12000} }
```

- 必须带 `revision`；服务端旧版本 → 409 `REVISION_CONFLICT`，不覆盖。
- 成功返回新 `revision` 与 `updated_at`；前端用返回值刷新本地状态，不自行 +1。
- 校验错误体：`{code, message, path, feature_id, details, remediation}`，UI 逐项就地显示。
- 几何写入（`POST /api/geometry`）同理：先校验 Shapely，再检查是否被标注引用。

## 5. 删除与引用

- 删除几何时若仍有标注引用 → **409**，返回引用列表（ID + 名称）。
- 只有显式 `?cascade=true` 才连同标注一起软删；级联删除要在 UI 里说明影响范围。
- 软删除不物理删行：`deleted_at` 置值，`restore=true` 恢复；FTS/RTree 行保留，查询过滤。

## 6. 并发

- 单用户场景，但仍必须检测冲突（同一 tab 双击、两个 tab、CLI 同时写）。
- 所有写接口走 SQLite 单写事务（WAL）；应用层不做重试覆盖，冲突就报错。
- `revision` 是唯一并发令牌；不允许"最后写入者赢"。

## 7. 安全

- 编辑端点仅 `--enable-edit` 时注册；未开启返回 404（不暴露能力）。
- 校验 `Origin`/`Host`；可选启动 token。
- 浏览器**绝不**直接写文件或 SQL；所有写入经 FastAPI。
- 前端校验只用于交互提示，**不是**安全或一致性防线。

## 8. QGIS 往返

1. `mapcreator export --qgis` → `build/qgis/geometry/*.geojson` + `build/qgis/annotations.geojson`（点 + 全部字段；`attrs` 为业务属性 JSON，`names` 为多语言名称 JSON）。
2. QGIS 打开，CRS 设 `EPSG:4326`；按比例尺配置标注预览。
3. 编辑后存回同路径。
4. `mapcreator geometry import --dir build/qgis/geometry` / `mapcreator annotations import --geojson build/qgis/annotations.geojson`。
5. 服务端校验 + `revision` 更新 + 重建。

注意：

- QGIS 是 GPL 软件，仅作**独立外部工具**，不链接、不随分发物捆绑。
- QGIS 会重排 GeoJSON 文本；导入后必须 `mapcreator format`，否则 diff 噪音淹没真实改动。
- 强拓扑（共享边、连通性）用 QGIS Topology Checker；构建期只做基础有效性。
- 往返必须保字段：导出→导入不得丢失 `attrs`、`names`、`rank`、`min/max_zoom`（用 golden 测试守）。

## 9. 验收

阶段 A（本分支，纯前端 UI）：

- [ ] 浏览/编辑共用一套外壳；浏览模式无工具栏/绘制手柄/保存按钮；桌面 1280×720 无溢出。
- [ ] 创建/编辑/删除点、线、面；拖拽锚点、顶点编辑、吸附生效。
- [ ] 属性编辑在**左栏**（kind、主名/多语言名、rank、min/max zoom、description、attrs）；非法输入被拒绝并就地显示；右侧详情保持只读。
- [ ] 撤销/重做覆盖绘制、拖拽与属性修改。
- [ ] 导出 `annotations.json` + `geometry.geojson`，可被 `mapcreator annotations import` 接受。
- [ ] 刷新页面后草稿清空且界面回到空态（不产生报错）。

阶段 B/C（后续分支，落库）：

- [ ] 保存到 `var/editor-test/annotations.db`，重启 `serve --editable` 后仍在；`world/annotations.db` 修改时间不变。

正式库追加验收：

- [ ] 创建/编辑/删除 点、线、面三类，各至少一条 E2E。
- [ ] 属性表单由 schema 生成；非法输入被拒绝并显示原因。
- [ ] 撤销/重做覆盖绘制与属性修改。
- [ ] 非法几何、重复 ID、越界坐标、缺失主名被拒绝。
- [ ] 编辑后刷新页面可见；`revision` 冲突返回 409。
- [ ] 删除被引用几何 → 409；级联删除可恢复。
