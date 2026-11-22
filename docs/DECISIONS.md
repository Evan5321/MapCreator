# 决策记录（DECISIONS / ADR）

> 变更规则：**已定**的决策只能由人类推翻；推翻时新增一条 ADR 并把旧条目标为 `superseded by ADR-XXXX`，不删除历史。
> 新增 ADR 用第 1 节的模板；简短决策可只写一行进第 2 节索引，重要决策在第 3 节展开。

## 1. ADR 模板

```markdown
## ADR-XXXX: 标题

- Status: proposed | accepted | superseded by ADR-YYYY
- Date: YYYY-MM-DD
- Context: 问题与约束
- Decision: 选择
- Consequences: 正面 / 负面 / 后续
- Alternatives considered: 候选与未采用原因
```

## 2. 索引

| ID | 决策 | 状态 | 理由摘要 | 备选 |
|---|---|---|---|---|
| D-001 | 本地优先 Web 应用（FastAPI + 浏览器） | 已定 | 跨平台、易截图/测试、复用 WebGL 生态 | 纯桌面 PySide6 |
| D-002 | MapLibre GL JS 作为渲染引擎 | 已定 | WebGL、标注碰撞、LOD 成熟 | Leaflet / OpenLayers / deck.gl |
| D-003 | Python 主导，JS 仅前端壳 | 已定 | 构建/校验/服务集中在一个语言 | 全 JS/TS |
| D-004 | 几何用 GeoJSON，标注用 SQLite | 已定 | 职责清晰；AI 可读 + SQL 可查 | 全 GeoJSON / GeoPackage |
| D-005 | RFC 7946 经纬度作为坐标格式 | 已定 | 工具链兼容性最好 | 自定义平面 CRS |
| D-006 | MVP 不引入瓦片，用缩放带分片 | 已定 | 小地图足够；避开 Windows 切片链 | MBTiles / PMTiles |
| D-007 | Terra Draw 编辑，QGIS 批量/拓扑 | 已定 | 复用成熟项目，不自研编辑器 | MapLibre Draw / 自研 |
| D-008 | 前端原生 JS + JSDoc，不用框架 | 已定 | 轻量、AI 可读、非 TS 主语言 | React / Vue / TS |
| D-009 | Noto Sans PBF + 本地 CJK 字体 | 已定 | 避开 Windows glyph 生成难题 | 自建 glyph 服务 |
| D-010 | 标注工作库 + 提交 SQL dump | 建议 | 兼顾 SQL 管理与 Git/AI 可读 | 提交二进制 DB / 纯 JSON |
| D-011 | AI 一切操作走 `mapcreator` CLI/JSON | 已定 | 可执行、可验证、可复现 | 手工 GUI / MCP |
| D-012 | 自研组件必须 ADR | 已定 | 防止重复造轮子 | 自由引入依赖 |
| D-013 | 世界=小范围有界区域、二维俯视；`bounds` 自动推导；`max_zoom=17` | 已定 | 与"虚构小地图"定位一致，避开投影/比例尺失真 | 完整星球；手填固定 bounds |
| D-014 | 标注 ID `anno.<kind>.<slug>` | 已定 | 与 `geo.*` 对称，替代三处冲突写法 | `poi.*`；无前缀 |
| D-015 | 点标注不建几何，坐标只在 `annotation.lon/lat` | 已定 | 单一真源，避免点位双写漂移 | 每点生成 Point 要素 |
| D-016 | 名称拆 `annotation_name` 子表（多语言+唯一主名）；渲染分片由构建期从 DB 生成 | 已定 | 支持中英并存、可按语种索引；分片是派生物 | `names` JSON 列；`name`/`name_en` |
| D-017 | 搜索 ≥3 字符走 trigram，<3 字符回退 LIKE | 已定 | 中文双字词可用，零新增依赖 | jieba 分词；只支持 ≥3 字符 |
| D-018 | 缩放带边界只由 `zoom_bands.toml` 定义（6 带） | 已定 | 构建确定性、golden 稳定 | 由 kind 反推带；不分带 |
| D-019 | 静态导出推迟到 M5 之后 | 已定 | 先保住浏览+搜索+编辑闭环 | MVP 内实现静态导出 |
| D-020 | UI 中文为主、文案 key 化、不引 i18n 框架 | 已定 | 轻量、AI 可读、保留扩展 | 中英双语框架；硬编码 |
| D-021 | 跨模块/API 载荷以 ID 为准 | 已定 | 载荷小、单一真源 | 宽表广播 |

## 3. 关键决策详情

### ADR-013: 世界模型 —— 二维俯视的有界区域

- Status: accepted（2026-11-03）
- Context: 架空世界没有真实地理；地图尺寸很小；若按球面/墨卡托处理，会引入高纬变形、比例尺失真与 ±180° 接缝等无收益的复杂度。
- Decision: 世界是有界区域，直接使用虚构经纬度作为坐标载体；不处理纬度限制与投影变形；构建期从数据推导 `bounds`；`max_zoom` 固定 17；比例尺仅近似显示。
- Consequences: 正向——工具链零改造、实现简单、渲染可控；负向——不能声称真实距离/面积，`planet_radius_km` 无实际意义；后续若要做"星球视图"需重开 ADR。
- Alternatives: 完整星球（需要自定义比例尺与环绕接缝处理）；自定义平面 CRS（破坏 QGIS/MapLibre/tippecanoe 默认假设）。

### ADR-014: 标注 ID 前缀统一为 `anno.`

- Status: accepted（2026-11-03）
- Context: 0.1 稿里同时出现 `poi.<kind>.<slug>`、`city.xxx`、无前缀三种写法；跨表 join 与 URL 状态需要唯一可判别的标识。
- Decision: `anno.<kind>.<slug>`，与几何的 `geo.<kind>.<slug>` 对称；DB 加粗校验，`validate` 用正则强校验；URL `sel=` 与 API 路径一律用它。
- Consequences: 正向——类型一眼可辨、可做前缀过滤；负向——"POI"这个业务词不再出现在 ID 里，与 UI 文案解耦（这其实是好事）。
- Alternatives: `poi.*`（语义覆盖不了大陆/大洋）；无前缀（与几何 ID 混淆）。

### ADR-015: 点标注不建 GeoJSON 几何

- Status: accepted（2026-11-03）
- Context: 点位既可以在 GeoJSON 存一份、再在 SQLite 存一份，也可以只存一处。双写会漂移，且构建校验要额外比对。
- Decision: 点坐标只存 `annotation.lon/lat`，`geometry_id` 恒 NULL；编辑器"点"工具直接创建标注；线/面才进入 GeoJSON。
- Consequences: 正向——无漂移、编辑路径最短；负向——GeoJSON 不再"包含所有几何"，需要文档明确说明（本决策与 DATA_SPEC §3 第 6 条）。
- Alternatives: 每点生成 Point 要素（统一但双写）；按 kind 区分（规则分叉，难维护）。

### ADR-016: 名称只在 SQLite，渲染分片由构建生成

- Status: accepted（2026-11-03）
- Context: 需求是"同一地标可同时显示中英文"；MapLibre 的 symbol layer 必须有文本字段才能画字；但名称不能重复写进 GeoJSON 真源。
- Decision: 名称存 `annotation_name` 子表（多语言 + 别名 + 唯一主名）；构建期从 DB 生成带 `id + name` 的渲染分片（派生物、可重建）；跨模块/API 只传 ID，详情按 ID 回查。
- Consequences: 正向——单一真源 + 可索引 + 渲染零额外请求；负向——渲染分片与 DB 可能短暂不一致（靠"编辑后重建"保证），`search_text` 需应用层维护。
- Alternatives: `names` JSON 列（不可索引）；`name`/`name_en` 两列（最多两语种）；渲染时按 ID 拉字典（2 万 feature-state，性能差）。

### ADR-017: 中文短词搜索走 LIKE 回退

- Status: accepted（2026-11-03）
- Context: FTS5 `trigram` 分词器对**少于 3 个字符**的查询不返回结果，而中文双字词（"上海""王城"）是最常见输入。
- Decision: ≥3 字符用 `MATCH`；1–2 字符回退 `LIKE '%q%'` 扫描（标注 ≤ 2 万，毫秒级）。
- Consequences: 正向——零新依赖、中文体验完整；负向——短词查询是 O(n) 扫描，数据量增长后需重新评估。
- Alternatives: `unicode61` + jieba 分词（质量好但引入词典维护）；只支持 ≥3 字符（中文体验不可接受）。

### ADR-018: 缩放带边界唯一权威在配置文件

- Status: accepted（2026-11-03）
- Context: 0.1 稿同时存在 `kinds.toml` 的 zoom 区间与 `zoom_bands.toml` 的带，且带边界只写在正文里；若两边都能定义边界，改一个 kind 会重排文件名与 golden。
- Decision: 6 个固定带，边界只由 `config/zoom_bands.toml` 定义；kind 的 zoom 区间只产生 style filter（带内可见性），不参与切分。
- Consequences: 正向——构建确定、golden 稳定、缓存友好；负向——新增一个"只看 z18"的 kind 需要同时扩带宽（显式动作）。
- Alternatives: 由 kind 的 `min_zoom` 反推带（抖动）；不分带（撞破载荷预算）。

### ADR-019: 静态导出推迟

- Status: accepted（2026-11-03）
- Context: 静态站点没有服务端，搜索/详情必须预生成索引；这会分叉出第二条数据通道，而 MVP 的价值在浏览+搜索+编辑闭环。
- Decision: MVP 不实现 `export --static`；M5 之后再评估（届时先定搜索方案）。
- Consequences: 正向——少一条路径、少一类 bug；负向——"离线单文件"需求暂不满足。
- Alternatives: MVP 内实现（成本高、收益晚）。

### ADR-020: 界面中文为主，不引 i18n 框架

- Status: accepted（2026-11-03）
- Context: 使用者是单人或小团队，界面语言需求稳定为中文；但标注名称必须多语言。
- Decision: UI 文案集中在 `web/i18n/zh.json` 并用 key 引用，不引 i18n 库；名称的多语言由 D-016 承担。
- Consequences: 正向——零依赖、可直接改文案；负向——将来加界面语言要手工加 key 文件（成本低）。
- Alternatives: 引 i18n 框架（为一个人维护两套文案不值）；硬编码中文（阻碍后续）。

### ADR-021: M0 标签用 DOM 层 + 屏幕空间碰撞

- Status: accepted（2026-11-19）
- Context: `ARCHITECTURE.md` §7 计划全部标注走 symbol layer；但仓库没有字体 glyph 与 icon sprite，且本轮不允许联网下载或新增依赖，symbol layer 的 `text-field` 无法渲染。
- Decision: TASK-0006 用 [web/src/labels.js](../web/src/labels.js)：按带拉取 `/api/data/{band}`，投影到屏幕坐标后做贪心碰撞剔除，标签为绝对定位 DOM；标注点仍由 style 的 circle 层渲染（每 kind 一层，`minzoom/maxzoom` 来自 `kinds.toml`）。
- Consequences: 正向——零字体资源即可看到分级标签与碰撞；负向——标签量大时 DOM 性能与渐隐/anchor 能力弱于 symbol layer，TASK-0011/0012 需在字体方案确定后评估切回。
- Alternatives: 自托管字体 glyph（需要下载/安装资源，规则禁止未批准的联网与安装）；用圆点代替文字（丢失名称信息）。

### ADR-022: 选中高亮用 DOM 环，不用 WebGL filter 层

- Status: accepted（2026-11-19）
- Context: TASK-0007 先用 circle 图层 + `setFilter(['==', ['id'], selectedId])` 做选中高亮；实测该层不出现在画布上（`['id']` 过滤与 GeoJSON feature id 的组合未生效，具体原因未深挖），而详情面板与 URL 状态均正常。
- Decision: 选中高亮改为 [web/src/labels.js](../web/src/labels.js) 中的 `.selection-ring` DOM 元素，位置由 `map.project` 计算并在标签重排时更新；标签层始终在其上方，圆点仍由样式 circle 层渲染。
- Consequences: 正向——高亮稳定可见、与 DOM 标签共用坐标系、无额外 layer/filter 状态；负向——环不随地图画布导出（截图/静态导出需另行处理），且只覆盖当前带内可见标签。
- Alternatives: 继续排查 `['id']` 过滤（时间成本高、收益仅为少一个 DOM 节点）；用 feature-state（需要 `promoteId` 并改构建产物）；把 `id` 写进 properties（破坏 ID 单一表达）。

### ADR-023: 浏览/编辑共用外壳，编辑先写临时测试库

- Status: accepted（2026-11-19）
- Context: 参考 civ-atlas 重做界面时，需要同时满足“浏览时不出现编辑控件”和“编辑器数据不污染 `world/` 真源”；同时要遵守单一写路径（AGENTS §2.1）。
- Decision: 前端一套外壳两种模式——浏览模式只挂地图与只读面板，编辑模式才挂载 `editor/pick/history` 的工具 UI；编辑写入走 dev-only 端点，目标固定为 `var/editor-test/annotations.db`（跨重启保留、首次从构建播种），几何写 `var/editor-test/geometry/`，服务端拒绝解析到 `world/` 的任何路径。正式库写入留给 TASK-0009。
- Consequences: 正向——可安全试用编辑器，`world/annotations.db` 不被触碰；负向——需要临时库与正式库两套读取路径，界面必须明确显示当前模式。
- Alternatives: 只导出文件不落库（无法验证重启持久化）；直接写 `world/`（违反用户要求与真源保护）。

### ADR-024: 编辑界面阶段只做 UI（前端草稿 + 导出），属性编辑放左栏

- Status: accepted（2026-11-19）
- Context: 分支 `feat/civ-atlas-ui` 的目标是把界面做出来，而不是打通写库链路；同时用户要求节点属性从右侧详情面板移到左栏，避免“看详情在右、改属性在右”与左栏工具分离。Terra Draw 1.40 需要 MapLibre 适配器，仓库未装。
- Decision:
  1. 该分支**只做浏览界面 + 编辑界面**，不做 TASK-0008 搜索/只读 SQL，不做后端写端点。
  2. 编辑草稿只存浏览器内存，通过“导出 `annotations.json` + `geometry.geojson`”交付；落库（`var/editor-test/` → `world/`）留给后续分支的 TASK-0009 阶段 B/C。
  3. 属性编辑作为**左栏“属性”分节**（工具栏下方），右侧 `#sidebar` 在编辑态退回只读详情；左栏编辑态顺序 工具 → 属性 → 图层 → 标注列表 → 世界信息。
  4. 绘制使用 Terra Draw + 官方适配器 `terra-draw-maplibre-gl`（已获批准，待安装），不自研适配层。
- Consequences: 正向——UI 可独立验收、`world/` 与后端零风险、属性与工具在同一视觉区域；负向——刷新即丢草稿，真实持久化与并发/冲突校验要等阶段 B/C，界面须明确标注“未保存”状态。
- Alternatives: 本分支同时也接临时库写端点（跨前后端，违背“只做 UI”）；属性继续留在右侧面板（用户已明确要求移动）；自研 MapLibre 适配层（需额外 ADR，维护成本高）。
