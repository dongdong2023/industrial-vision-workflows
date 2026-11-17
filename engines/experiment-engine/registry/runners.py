"""Hash-pinned trusted Python runner registry, with no shell expansion."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from ivw.common import ROOT, child, file_hash, guard_write, identifier, read_json, save_json, stamp


def register(name, path, store):
    identifier(name)
    path = guard_write(path)
    if path.suffix != ".py" or not path.is_file():
        raise ValueError("runner 必须是实际存在的本地 Python 文件")
    if name in read_json(ROOT / "config/runners.json"):
        raise ValueError("不能替换内置 runner")
    record = {"name": name, "file": str(path), "sha256": file_hash(path), "registered_at": stamp(),
              "trust": "user-reviewed-local-python; not a sandbox"}
    save_json(Path(store) / "runners" / (name + ".json"), record, exclusive=True)
    return record


def resolve(name, store):
    identifier(name)
    builtins = read_json(ROOT / "config/runners.json")
    if name in builtins:
        path = child(ROOT, builtins[name]["file"])
        return {"name": name, "file": str(path), "sha256": file_hash(path), "purpose": builtins[name]["purpose"]}
    record = read_json(Path(store) / "runners" / (name + ".json"))
    path = guard_write(record["file"])
    if file_hash(path) != record["sha256"]:
        raise ValueError("runner 注册后已变更；使用新版本名称重新登记")
    return record
