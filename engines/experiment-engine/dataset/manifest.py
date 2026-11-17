"""Dataset checks that can be performed without a vision library."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from ivw.common import digest, read_json, save_json


def audit(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1 or data.get("task") not in {"detection", "pointcloud", "video-action"}:
        raise ValueError("不支持的数据集协议")
    if data.get("evidence_level") not in {"synthetic", "offline", "field"}:
        raise ValueError("必须声明数据证据等级")
    if data["task"] == "pointcloud" and data.get("coordinate_unit") != "m":
        raise ValueError("点云评测必须显式使用米；先确认并转换坐标")
    samples = data.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("数据集不能为空")
    ids, groups, content_splits = set(), {}, {}
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("样本必须为对象")
        sid, group, split = sample.get("id"), sample.get("group"), sample.get("split")
        if not isinstance(sid, str) or not sid or sid in ids:
            raise ValueError("样本 ID 缺失或重复")
        ids.add(sid)
        if not isinstance(group, str) or not group or split not in {"train", "validation", "test"}:
            raise ValueError("样本必须有 group 与有效 split")
        if group in groups and groups[group] != split:
            raise ValueError(f"分组泄漏: {group}")
        groups[group] = split
        if not isinstance(sample.get("ground_truth"), list) or not isinstance(sample.get("observations"), list):
            raise ValueError("ground_truth 和 observations 必须为列表")
        if sample.get("annotation_status", "verified") != "verified":
            raise ValueError("未确认的标注不能当作真值或空场负例")
        if "slice" in sample and (not isinstance(sample["slice"], str) or not sample["slice"]):
            raise ValueError("slice 必须为非空字符串")
        # An explicit content hash describes the raw capture, not annotations or transformed IDs.
        raw_hash = sample.get("content_sha256")
        if raw_hash:
            if not isinstance(raw_hash, str) or len(raw_hash) != 64 or any(c not in "0123456789abcdef" for c in raw_hash):
                raise ValueError("content_sha256 无效")
            if raw_hash in content_splits and content_splits[raw_hash] != split:
                raise ValueError("重复采集内容跨集合泄漏")
            content_splits[raw_hash] = split
    return {"samples": len(samples), "groups": len(groups), "splits": sorted(set(groups.values())),
            "limitations": ["标签准确性、未声明的重复采集和现场代表性仍需独立核查"]}


def register(path, store):
    data = read_json(path)
    result = audit(data)
    version = digest(data)
    target = Path(store) / "datasets" / (version + ".json")
    if target.exists():
        if digest(read_json(target)) != version:
            raise ValueError("数据集注册记录被修改")
    else:
        save_json(target, data, exclusive=True)
    return {"dataset_id": version, "path": str(target.resolve()), "audit": result}
