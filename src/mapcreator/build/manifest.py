"""manifest 生成：输入哈希、计数、图层统计、构建版本；**禁止时间戳**。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..errors import DataValidationError

TASK = "TASK-0005"
REQUIRED_KEYS = ("schema_version", "build_version", "input_hash", "bounds", "counts", "world")


def _label_for(path: Path, root: Path | None) -> str:
    """稳定的输入标识：尽量用相对仓库根的路径，避免绝对路径进入哈希。"""
    if root is not None:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            pass
    return path.name


def input_hash(paths: list[Path], *, root: Path | None = None) -> str:
    """确定性哈希：`相对路径 + sha256(内容)` 排序后取总哈希。

    只依赖内容与路径，不依赖文件修改时间与遍历顺序。
    """
    lines: list[str] = []
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{_label_for(path, root)}:{digest}")
    payload = "\n".join(sorted(lines))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write(manifest: dict[str, Any], out: Path) -> None:
    """稳定键序写出 JSON（LF、无时间戳）。"""
    text = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8", newline="\n")


def read(path: Path) -> dict[str, Any]:
    """读取并有基本 schema 校验。"""
    if not path.is_file():
        raise DataValidationError(
            code="MANIFEST_MISSING",
            message=f"manifest 不存在：{path.name}",
            path=path,
            remediation="先运行 `mapcreator build`",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DataValidationError(
            code="MANIFEST_INVALID_JSON",
            message=f"{path.name}: JSON 解析失败：{exc.msg}（第 {exc.lineno} 行）",
            path=path,
            remediation="重新运行 `mapcreator build` 生成",
        ) from exc
    if not isinstance(payload, dict):
        raise DataValidationError(
            code="MANIFEST_INVALID_ROOT",
            message=f"{path.name}: 根对象必须是 JSON 对象",
            path=path,
            remediation="重新运行 `mapcreator build` 生成",
        )
    missing = [key for key in REQUIRED_KEYS if key not in payload]
    if missing:
        raise DataValidationError(
            code="MANIFEST_INCOMPLETE",
            message=f"{path.name}: 缺少字段 {missing}",
            path=path,
            remediation="重新运行 `mapcreator build` 生成",
        )
    return payload
