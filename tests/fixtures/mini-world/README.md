# mini-world

所有 golden/E2E 的基准夹具：**1** 块大陆、**1** 片海、**2** 条河、**1** 条山脉、**2** 座城、**5** 个 POI、**1** 条地铁线。

内容由 TASK-0003 生成，必须满足 `docs/DATA_SPEC.md` 的全部校验规则。禁止依赖真实世界数据。

创建后的结构（与 `world/` 同构）：

```text
mini-world/
├─ world.json
├─ geometry/{land,water,rivers,terrain,roads,transit,parks}.geojson
└─ annotations.sql
```