# world/ — 真源目录

| 路径 | 性质 | 说明 |
|---|---|---|
| `world.json` | 提交 | 世界元数据、图层清单、`schema_version` |
| `geometry/*.geojson` | 提交 | 几何真源（**不含名称**，见 DATA_SPEC §3） |
| `annotations.db` | **忽略** | SQLite 工作库，由 `db restore` 从 dump 生成 |
| `annotations.sql` | 提交 | 逻辑表 dump（唯一可版本化的标注真源） |

当前状态：**骨架**。`geometry/*.geojson` 是空 `FeatureCollection`；`annotations.db` 与 `annotations.sql` 尚未生成（需要 TASK-0004 的 `db` 子命令）。

约束提醒：

- 点标注**不产生**几何要素（D-015），不要在这里加 `points.geojson`。
- `properties` 只允许 `DATA_SPEC` §3 白名单的键；不要写 `name` / `rank` / `layer`。
- 不要手工编辑 `build/` 下的任何内容。
