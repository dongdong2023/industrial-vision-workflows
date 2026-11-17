"""Observe protected projects without changing their Git index or files."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ivw.common import digest, file_hash, read_json, save_json


def snapshot():
    documents = {}
    for example in (ROOT / "examples/projects").glob("*.json"):
        spec = read_json(example)
        documents.setdefault(str(Path(spec["source_root"]).resolve()), []).extend(spec["documents"])
    result = {}
    for source in read_json(ROOT / "config/protection.json")["read_only_roots"]:
        root = Path(source).resolve()
        entry = {"exists": root.is_dir(), "documents": {}}
        for relative in documents.get(str(root), []):
            path = root / relative
            entry["documents"][relative] = file_hash(path) if path.is_file() else None
        for name, args in (("head", ["rev-parse", "HEAD"]),
                           ("status", ["status", "--porcelain=v1", "--untracked-files=all"]),
                           ("diff", ["diff", "HEAD", "--binary", "--no-ext-diff", "--no-textconv"])):
            command = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                                     env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
            entry[name] = {"exit_code": command.returncode, "sha256": digest(command.stdout.hex())}
        entry["coverage"] = "Git HEAD/status/diff 与指定文档摘要；非 Git 项目仅核对指定文档"
        result[str(root)] = entry
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--compare", type=Path)
    args = parser.parse_args()
    result = snapshot()
    save_json(args.out, result, exclusive=True)
    unchanged = not args.compare or result == read_json(args.compare)
    print(json.dumps({"snapshot": str(args.out.resolve()), "unchanged": unchanged}, ensure_ascii=False))
    return 0 if unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
