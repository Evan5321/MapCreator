# tasks/

任务清单的**唯一**来源是仓库根目录的 [`TODO.md`](../TODO.md)。本目录只放单个任务的展开文件（在任务复杂到需要独立文档时才创建）。

## 命名

`TASK-0007-<slug>.md`，与 `TODO.md` 中的编号一致。

## 模板

```markdown
# TASK-0007: 标题

- Status: pending | in_progress | done | blocked
- Milestone: M1
- Owner: AI Agent
- Context: 相关 docs/文件链接
- Goal: 一句话
- Scope: 允许修改的范围
- Out of scope: 明确不做
- Acceptance criteria:
  - [ ] ...
- Evidence required: 命令/测试/截图
- Dependencies: 无 / TASK-xxxx
- Notes: 风险与假设
```

## 规则

- 一个任务一个垂直切片。
- 验收标准必须可命令化（能跑、能截图、能比对）。
- 与 `DATA_SPEC.md` 冲突时先改文档（spec-first）。