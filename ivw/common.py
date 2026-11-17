"""Shared local artifact primitives; no model or network dependencies."""
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    def reject_constant(value):
        raise ValueError(f"JSON 不允许非有限数值: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), parse_constant=reject_constant)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, value, exclusive=False):
    path = Path(path)
    guard_write(path)
    content = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive publication never replaces an existing record.
    with path.open("x" if exclusive else "w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def child(root, relative):
    root = Path(root).resolve()
    relative = Path(relative)
    candidate = root / relative
    path = candidate.resolve()
    if relative.is_absolute() or ".." in relative.parts or path != candidate or path == root or not path.is_relative_to(root):
        raise ValueError(f"路径越界: {relative}")
    return path


def guard_write(path):
    path = Path(path).resolve()
    vendor = (ROOT / "vendor").resolve()
    if path == vendor or path.is_relative_to(vendor):
        raise ValueError(f"固定上游目录禁止写入: {path}")
    protection = read_json(ROOT / "config/protection.json")
    for source in protection["read_only_roots"]:
        source = Path(source).resolve()
        if path == source or path.is_relative_to(source):
            raise ValueError(f"只读项目禁止写入: {path}")
    return path


def guard_workspace(path):
    path = guard_write(path)
    for source in read_json(ROOT / "config/protection.json")["read_only_roots"]:
        if Path(source).resolve().is_relative_to(path):
            raise ValueError(f"工作区不能是只读项目的祖先: {path}")
    return path


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", value):
        raise ValueError(f"无效标识符: {value}")
    return value


def number(value, name, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} 必须是有限数值")
    if minimum is not None and value < minimum or maximum is not None and value > maximum:
        raise ValueError(f"{name} 超出范围")
    return value


def runtime_env():
    return dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
