"""Build a source-only, allowlisted Portable delivery archive."""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ivw.common import child, guard_write, read_json
from ivw.integration import verify_vendor

ALLOWED_ROOTS = {"adapters", "agents", "checks", "config", "docs", "engines", "examples",
                 "ivw", "profiles", "scripts", "skills", "tests", "workflows"}
ALLOWED_FILES = {"README.md", "AGENTS.md", ".gitignore", "ivw.py", "upstream.lock.json"}
ALLOWED_SUFFIXES = {".py", ".md", ".json", ".ps1"}


def build(output):
    output = guard_write(output)
    if output.suffix.lower() != ".zip":
        raise ValueError("共享包输出必须为 .zip")
    verified = verify_vendor()
    names = read_json(ROOT / "config/share-files.json")["files"]
    if len(names) != len(set(names)):
        raise ValueError("共享清单存在重复路径")
    for name in names:
        path = Path(name)
        if (name not in ALLOWED_FILES and (path.parts[0] not in ALLOWED_ROOTS or path.suffix not in ALLOWED_SUFFIXES)
                or "__pycache__" in path.parts):
            raise ValueError(f"非源码路径禁止进入共享包: {name}")
    for dataset in (ROOT / "examples/datasets").glob("*.json"):
        if read_json(dataset).get("evidence_level") != "synthetic":
            raise ValueError("共享示例只允许合成数据；客户数据仅作本地引用")
    names = sorted([*names, *("vendor/loopforge/" + n for n in read_json(ROOT / "upstream.lock.json")["files"])])
    payload = {}
    for name in names:
        source = child(ROOT, name)
        if source != ROOT / name or any(p.is_symlink() for p in [ROOT / name, *(ROOT / name).parents] if p != ROOT):
            raise ValueError(f"共享包禁止链接或非规范路径: {name}")
        payload[name] = source.read_bytes()
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in payload.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in payload.items():
            archive.writestr(name, data)
        archive.writestr("PACKAGE-MANIFEST.json", json.dumps({"schema_version": 1, "files": hashes}, indent=2) + "\n")
    return {"archive": str(output), "files": len(payload), **verified,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.output), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
