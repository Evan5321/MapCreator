# 第三方资产署名（ATTRIBUTION）

每个字体/图标资产都必须在此登记：来源、版本/提交、许可证、SHA-256、落盘文件。
未登记的资产不得进入 `build/`（`build/assets.py` 会校验）。

| 资产 | 版本/提交 | 来源 | 许可证 | SHA-256 | 文件 |
|---|---|---|---|---|---|
| _（暂无，等待 TASK-0006 引入）_ | | | | | |

## 计划引入

| 资产 | 来源 | 许可证（待核对） |
|---|---|---|
| Noto Sans glyph PBF | https://github.com/openmaptiles/fonts | 以仓库 LICENSE 为准（Noto 为 OFL） |
| Noto 字体源 | https://github.com/notofonts/noto-fonts | OFL-1.1 |
| Maki 图标 | https://github.com/mapbox/maki | 以仓库 LICENSE 为准 |
| Temaki 图标 | https://github.com/rapideditor/temaki | 以仓库 LICENSE 为准 |

## 规则

- 二进制资产不参与文本 diff；用 SHA-256 记录版本。
- 许可证以仓库 LICENSE 原文为准；标注"待核对"的必须在引入时补齐。
- CJK 字形使用系统字体（`localIdeographFontFamily`），**不**生成 glyph PBF。