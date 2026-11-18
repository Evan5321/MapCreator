# migrations/

- 命名：`NNNN_<desc>.sql`（如 `0001_init.sql`），按序号顺序执行。
- 必须**幂等可重放**（`IF NOT EXISTS` / 先判断再改）。
- 每次 DDL 变更把 `meta.schema_version` +1。
- 破坏性迁移前必须 `mapcreator backup`，并在 `docs/STATUS.md` 记录。
- 迁移由 TASK-0004 的 `repo.py` 执行；不要手工在数据库上跑 DDL 后忘记登记。