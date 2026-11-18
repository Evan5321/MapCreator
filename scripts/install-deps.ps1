<#
.SYNOPSIS
    MapCreator 依赖安装脚本（由人类手动执行）。

.DESCRIPTION
    本脚本会从 PyPI 与 npm 拉取依赖，并下载 Playwright 的 Chromium。
    它**不修改源码**、**不生成业务数据**，只安装依赖。

    运行前请确认：
      - 已安装 Python 3.12+、uv、Node.js 20+、npm
      - 网络可访问 PyPI、registry.npmjs.org、Playwright CDN

.PARAMETER SkipPython
    跳过 uv sync（不安装 Python 依赖）。

.PARAMETER SkipNode
    跳过 npm install / npm ci（不安装前端依赖）。

.PARAMETER SkipPlaywright
    跳过浏览器下载（E2E 截图需要，但可以先不装）。

.PARAMETER DryRun
    只打印将执行的命令，不实际执行。

.EXAMPLE
    pwsh -NoProfile -File scripts\install-deps.ps1 -DryRun
    pwsh -NoProfile -File scripts\install-deps.ps1
#>
#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$SkipPython,
    [switch]$SkipNode,
    [switch]$SkipPlaywright,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$script:Failed = @()
$script:Done = @()

function Write-Header([string]$Text) {
    Write-Host ''
    Write-Host "==> $Text" -ForegroundColor Cyan
}

function Assert-Tool([string]$Name, [string]$Hint) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Write-Host "  [缺失] $Name —— $Hint" -ForegroundColor Yellow
        return $false
    }
    Write-Host "  [ok]   $Name -> $($cmd.Source)" -ForegroundColor DarkGray
    return $true
}

function Invoke-Step([string]$Label, [scriptblock]$Body) {
    Write-Header $Label
    if ($DryRun) {
        Write-Host '  (DryRun：跳过实际执行)' -ForegroundColor DarkYellow
        return
    }
    try {
        & $Body
        $script:Done += $Label
        Write-Host "  [完成] $Label" -ForegroundColor Green
    }
    catch {
        $script:Failed += "$Label :: $($_.Exception.Message)"
        Write-Host "  [失败] $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host '==================================================' -ForegroundColor DarkCyan
Write-Host ' MapCreator 依赖安装（手动执行）' -ForegroundColor DarkCyan
Write-Host '==================================================' -ForegroundColor DarkCyan
Write-Host " 仓库根目录: $repoRoot"
if ($DryRun) { Write-Host ' 模式: DryRun（只打印，不执行）' -ForegroundColor DarkYellow }

# ---------------------------------------------------------------- 0. 前置检查
Write-Header '0/4 检查前置工具'
$hasUv = Assert-Tool 'uv' '安装：https://github.com/astral-sh/uv'
$hasNpm = Assert-Tool 'npm' '安装 Node.js 20 LTS+：https://github.com/nodejs/node'
Assert-Tool 'git' '安装：https://git-scm.com/' | Out-Null
Write-Host '  [info] Python 由 uv 管理；ruff/mypy/pytest 等都在 dev 依赖组里' -ForegroundColor DarkGray

# ---------------------------------------------------------------- 1. Python
if ($SkipPython) {
    Write-Host ''
    Write-Host '[-] 跳过 Python 依赖（-SkipPython）' -ForegroundColor DarkYellow
}
elseif (-not $hasUv) {
    $script:Failed += 'Python 依赖 :: 未找到 uv'
    Write-Host ''
    Write-Host '[!] 无法执行 uv sync（uv 未安装）' -ForegroundColor Red
}
else {
    Invoke-Step '1/4 uv sync（Python 依赖 + uv.lock）' {
        uv sync
        if ($LASTEXITCODE -ne 0) { throw "uv sync 退出码 $LASTEXITCODE" }
    }
}

# ---------------------------------------------------------------- 2. Node
if ($SkipNode) {
    Write-Host ''
    Write-Host '[-] 跳过前端依赖（-SkipNode）' -ForegroundColor DarkYellow
}
elseif (-not $hasNpm) {
    $script:Failed += '前端依赖 :: 未找到 npm'
    Write-Host ''
    Write-Host '[!] 无法执行 npm 安装（npm 未安装）' -ForegroundColor Red
}
else {
    $hasLock = Test-Path -LiteralPath (Join-Path $repoRoot 'package-lock.json')
    if ($hasLock) {
        Invoke-Step '2/4 npm ci（按 package-lock.json 精确安装）' {
            npm ci
            if ($LASTEXITCODE -ne 0) { throw "npm ci 退出码 $LASTEXITCODE" }
        }
    }
    else {
        Invoke-Step '2/4 npm install（首次安装并生成 package-lock.json）' {
            npm install
            if ($LASTEXITCODE -ne 0) { throw "npm install 退出码 $LASTEXITCODE" }
        }
    }
}

# ---------------------------------------------------------------- 3. Playwright
if ($SkipPlaywright) {
    Write-Host ''
    Write-Host '[-] 跳过 Playwright 浏览器（-SkipPlaywright）' -ForegroundColor DarkYellow
}
elseif (-not $hasUv) {
    $script:Failed += 'Playwright :: 未找到 uv'
}
else {
    # 国内镜像优先；已有环境变量时尊重用户设置。
    if (-not $env:PLAYWRIGHT_DOWNLOAD_HOST) {
        $env:PLAYWRIGHT_DOWNLOAD_HOST = 'https://cdn.npmmirror.com/binaries/playwright'
    }
    Invoke-Step '3/4 playwright install chromium（约 150 MB）' {
        uv run playwright install chromium
        if ($LASTEXITCODE -ne 0) { throw "playwright install 退出码 $LASTEXITCODE" }
    }
}

# ---------------------------------------------------------------- 4. 自检
Write-Header '4/4 环境自检'
if ($DryRun) {
    Write-Host '  (DryRun：跳过)' -ForegroundColor DarkYellow
}
elseif ($hasUv) {
    try {
        uv run mapcreator doctor --json
        if ($LASTEXITCODE -ne 0) { throw "退出码 $LASTEXITCODE" }
    }
    catch {
        Write-Host '  [提示] doctor 未能执行；可先用：uv run python -c "import sqlite3;print(sqlite3.sqlite_version)"' -ForegroundColor DarkYellow
    }
}

# ---------------------------------------------------------------- 汇总
Write-Host ''
Write-Host '==================================================' -ForegroundColor DarkCyan
if ($script:Failed.Count -eq 0) {
    Write-Host ' 全部步骤完成。' -ForegroundColor Green
}
else {
    Write-Host ' 有步骤失败：' -ForegroundColor Red
    $script:Failed | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
}
Write-Host '==================================================' -ForegroundColor DarkCyan
Write-Host ''
Write-Host '下一步：' -ForegroundColor Cyan
Write-Host '  uv run mapcreator doctor --json    # TASK-0002 之后可用'
Write-Host '  uv run mapcreator build --json'
Write-Host '  uv run mapcreator serve'
Write-Host ''
Write-Host '可选外部工具（本脚本不会安装）：' -ForegroundColor DarkGray
Write-Host '  QGIS      : https://qgis.org/  （批量/拓扑编辑，GPL，仅外部工具）'
Write-Host '  Docker    : https://www.docker.com/  （后续 tippecanoe 切片）'
Write-Host '  tippecanoe: https://github.com/felt/tippecanoe  （建议 WSL/Docker）'

if ($script:Failed.Count -gt 0) { exit 1 }
exit 0
