#!/usr/bin/env bash
# MapCreator 依赖安装脚本（由人类手动执行；不要交给 AI 自动跑）
#
# 会联网拉取：PyPI、registry.npmjs.org、Playwright 浏览器 CDN
# 不会修改源码、不生成数据。
#
# 用法：
#   bash scripts/install-deps.sh              # 全量安装
#   bash scripts/install-deps.sh --dry-run    # 只打印命令
#   bash scripts/install-deps.sh --skip-playwright
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DRY_RUN=0
SKIP_PYTHON=0
SKIP_NODE=0
SKIP_PLAYWRIGHT=0
FAILED=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --skip-python) SKIP_PYTHON=1 ;;
    --skip-node) SKIP_NODE=1 ;;
    --skip-playwright) SKIP_PLAYWRIGHT=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *) echo "未知参数：$arg（--help 查看用法）" >&2; exit 2 ;;
  esac
done

have() { command -v "$1" >/dev/null 2>&1; }

section() { printf '\n==> %s\n' "$1"; }

run() {
  local label="$1"; shift
  section "$label"
  printf '    %s\n' "$*"
  if [ "$DRY_RUN" -eq 1 ]; then
    echo '  (DryRun：跳过实际执行)'
    return 0
  fi
  if "$@"; then
    echo "  [完成] $label"
  else
    echo "  [失败] $label" >&2
    FAILED=$((FAILED + 1))
  fi
}

echo '=================================================='
echo ' MapCreator 依赖安装（手动执行）'
echo '=================================================='
echo " 仓库根目录: $REPO_ROOT"
[ "$DRY_RUN" -eq 1 ] && echo ' 模式: DryRun（只打印，不执行）'

section '0/4 检查前置工具'
have uv  && echo '  [ok]   uv'  || { echo '  [缺失] uv —— https://github.com/astral-sh/uv'; FAILED=$((FAILED + 1)); }
have npm && echo '  [ok]   npm' || { echo '  [缺失] npm —— https://github.com/nodejs/node'; FAILED=$((FAILED + 1)); }
have git && echo '  [ok]   git' || echo '  [缺失] git（建议安装）'

if [ "$SKIP_PYTHON" -eq 1 ]; then
  echo; echo '[-] 跳过 Python 依赖（--skip-python）'
elif have uv; then
  run '1/4 uv sync（Python 依赖 + uv.lock）' uv sync
else
  echo; echo '[!] 无法执行 uv sync（uv 未安装）' >&2
fi

if [ "$SKIP_NODE" -eq 1 ]; then
  echo; echo '[-] 跳过前端依赖（--skip-node）'
elif have npm; then
  if [ -f package-lock.json ]; then
    run '2/4 npm ci（按 package-lock.json 安装）' npm ci
  else
    run '2/4 npm install（首次安装并生成 package-lock.json）' npm install
  fi
else
  echo; echo '[!] 无法执行 npm 安装（npm 未安装）' >&2
fi

if [ "$SKIP_PLAYWRIGHT" -eq 1 ]; then
  echo; echo '[-] 跳过 Playwright 浏览器（--skip-playwright）'
elif have uv; then
  # 国内镜像优先；已有环境变量时尊重用户设置。
  export PLAYWRIGHT_DOWNLOAD_HOST="${PLAYWRIGHT_DOWNLOAD_HOST:-https://cdn.npmmirror.com/binaries/playwright}"
  run '3/4 playwright install chromium（约 150 MB）' uv run playwright install chromium
fi

section '4/4 环境自检'
if [ "$DRY_RUN" -eq 1 ]; then
  echo '  (DryRun：跳过)'
elif have uv; then
  uv run mapcreator doctor --json || echo '  [提示] doctor 报告了缺失项，按上面的 remediation 处理。'
fi

echo
echo '=================================================='
if [ "$FAILED" -eq 0 ]; then
  echo ' 全部步骤完成。'
else
  echo " 有 $FAILED 个步骤失败，请查看上方输出。"
fi
echo '=================================================='
echo
echo '下一步：'
echo '  uv run mapcreator doctor --json'
echo '  uv run mapcreator build --json'
echo '  uv run mapcreator serve'
echo
echo '可选外部工具（本脚本不会安装）：QGIS / Docker / tippecanoe'

[ "$FAILED" -eq 0 ] && exit 0 || exit 1
