# 编辑器（EDITOR）

> 目标 ≤ 150 行。字段规则见 [`DATA_SPEC.md`](DATA_SPEC.md)，端点见 [`ARCHITECTURE.md`](ARCHITECTURE.md) §6。
> 一句话：**Web 编辑器管日常标注与线面几何，QGIS 管批量与拓扑，自研桌面编辑器不做。**

## 1. 策略

| 方案 | 用途 | 决策 |
|---|---|---|
| Web 编辑器（Terra Draw） | 日常点/线/面 + 标注编辑 | MVP 必做 |
| QGIS | 批量绘制、拓扑检查、海岸线/边界精修 | 可选，不装也能完成 MVP |
| 自研桌面编辑器 | 产品化 | 暂不做；需要时先 ADR |

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
- 撤销/重做：用 Terra Draw 自带能力；**先核对锁定版本的 API**，不凭记忆写。
- 属性表单：基础字段（多语言名称、rank、min/max zoom、描述）专门渲染；业务属性用 `@json-editor/json-editor` 按 `attrs_schema` 生成。
- 名称编辑：至少一个主名（`is_primary`）；可加任意语种与别名；不能删到零个。
- 保存：一次提交一个或多个要素 → 服务端逐条校验 → 返回逐要素错误（部分成功要明确列出）。
- 软删除 + 恢复；删除需二次确认。
- 锚点拖动：线/面标注的 `lon/lat` 可拖动优化位置，不影响几何。

## 4. 保存协议

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

## 9. 验收（M3）

- [ ] 创建/编辑/删除 点、线、面三类，各至少一条 E2E。
- [ ] 属性表单由 schema 生成；非法输入被拒绝并显示原因。
- [ ] 撤销/重做覆盖绘制与属性修改。
- [ ] 非法几何、重复 ID、越界坐标、缺失主名被拒绝。
- [ ] 编辑后刷新页面可见；`revision` 冲突返回 409。
- [ ] 删除被引用几何 → 409；级联删除可恢复。
