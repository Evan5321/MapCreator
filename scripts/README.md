# scripts/ — 手动安装与维护脚本

这些脚本**由人类执行**。AI Agent 不得自行运行任何联网安装（见 `AGENTS.md` 规则 11）。

| 脚本 | 平台 | 作用 | 是否联网 |
|---|---|---|---|
| `install-deps.ps1` | Windows / PowerShell 5.1+ / pwsh 7 | `uv sync` → `npm ci\|install` → `playwright install chromium` → `doctor` | 是 |
| `install-deps.sh` | WSL / Git Bash / macOS / Linux | 同上 | 是 |

## 用法

```powershell
# 先看将执行什么（不联网、不安装）
pwsh -NoProfile -File scripts\install-deps.ps1 -DryRun

# 真正安装
pwsh -NoProfile -File scripts\install-deps.ps1

# 只装 Python
pwsh -NoProfile -File scripts\install-deps.ps1 -SkipNode -SkipPlaywright
```

> 没有 PowerShell 7（`pwsh`）时，用系统自带的 Windows PowerShell 5.1：
>
> ```powershell
> powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\install-deps.ps1 -DryRun
> powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\install-deps.ps1
> ```

```bash
bash scripts/install-deps.sh --dry-run
bash scripts/install-deps.sh
```

## 参数

| 参数 | ps1 | sh | 说明 |
|---|---|---|---|
| 预演 | `-DryRun` | `--dry-run` | 只打印命令 |
| 跳过 Python | `-SkipPython` | `--skip-python` | 不跑 `uv sync` |
| 跳过前端 | `-SkipNode` | `--skip-node` | 不跑 `npm` |
| 跳过浏览器 | `-SkipPlaywright` | `--skip-playwright` | 不下载 Chromium |

## 首次安装会发生什么

1. `uv sync`：创建 `.venv`，解析并写出 `uv.lock`。
2. `npm install`：创建 `node_modules`，解析并写出 `package-lock.json`（第二次起脚本自动改用 `npm ci`）。
3. `playwright install chromium`：下载浏览器到用户目录（约 150 MB）。
4. `mapcreator doctor --json`：环境自检；必需项缺失时退出码 3（2026-11-18 起已可用）。

## 注意

- 脚本不会修改源码、不会写 `world/` 或 `build/`。
- `package.json` 里的版本是范围，不是锁定值；锁定结果以生成的 lock 文件为准。
- 安装失败时先看输出里的 `[失败]` 行，再对照 `docs/ENVIRONMENT.md` 核对版本要求。
- 完成后应提交 `uv.lock` 与 `package-lock.json`。
