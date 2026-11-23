# TASK-0009 阶段 A — 任务清单

- [x] 1. `web/src/history.js`：快照栈（上限 100、去重、undo/redo）
- [x] 2. `web/src/inspector.js`：左栏属性表单（kind/多语言名/rank/zoom/description/attrs、就地校验、保存/取消/删除）
- [x] 3. `web/src/editor.js`：Terra Draw 装配（适配器 + 5 模式）、工具切换、草稿文档、历史提交、ID 生成、导出
- [x] 4. `web/src/shell.js`：`setMode()`（顶栏文案 + body 类）
- [x] 5. `web/index.html` + `web/src/main.js`：编辑模式切换、导出按钮、编辑态点击分派、`window.__app` 探针
- [x] 6. `web/src/style.css`：工具条、表单、编辑态样式；1280×720 不溢出
- [x] 7. `docs/DEPENDENCIES.md`：更正适配器包名与版本
- [x] 8. 门禁：`npm run check`、`npm run build`
- [x] 9. 视觉/交互验证：Playwright 1280×720 浏览态无编辑控件、绘制点线面、属性保存、拖拽、撤销重做、导出；截图与 console 证据
- [x] 10. 导出数据校验：Python `load_export` 接受 `annotations.json`
- [x] 11. 收口：`TODO.md` 勾选阶段 A、更新 `docs/STATUS.md`
