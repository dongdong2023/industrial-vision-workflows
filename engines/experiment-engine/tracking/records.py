"""Read and verify immutable experiment artifacts before consumers use them."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from ivw.common import child, digest, file_hash, read_json


def load_run(path):
    path = Path(path).resolve()
    record = read_json(path)
    if not isinstance(record, dict):
        raise ValueError("实验记录必须为对象")
    expected = record.pop("record_hash", None)
    if not expected or digest(record) != expected:
        raise ValueError("实验记录摘要不一致")
    record["record_hash"] = expected
    if record["status"] == "completed" and not {"predictions.json", "input.json", "config.json"}.issubset(record["artifact_hashes"]):
        raise ValueError("完成实验缺少固定输入、配置或预测摘要")
    for name, expected in record["artifact_hashes"].items():
        target = child(path.parent, name)
        if not target.is_file() or file_hash(target) != expected:
            raise ValueError(f"实验产物被修改: {name}")
    if digest(read_json(path.parent / "config.json")) != record["config_hash"]:
        raise ValueError("实验配置摘要不一致")
    return record
