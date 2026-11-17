"""Independent deterministic metrics, consuming frozen predictions and ground truth."""
import argparse
import importlib.util
import json
import sys
import uuid
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
ROOT = ENGINE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ROOT / "engines/experiment-engine"))
from ivw.common import child, digest, file_hash, guard_workspace, number, read_json, save_json, stamp
from dataset.manifest import audit
from tracking.records import load_run
from reporting.matching import match
from detection import metrics as detection
from pointcloud import metrics as pointcloud


def fixed_module(name, relative):
    # Fixed in-tree paths accommodate the public hyphenated architecture directories.
    spec = importlib.util.spec_from_file_location(name, ENGINE / relative / "metrics.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


video = fixed_module("video_action_metrics", "video-action")
edge = fixed_module("edge_metrics", "edge-performance")


def ratios(counts):
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    return {"precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None}


def evaluate(record_path, dataset_path, protocol_path, store):
    record_path = Path(record_path).resolve()
    run = load_run(record_path)
    if run["status"] != "completed":
        raise ValueError("失败或超时实验不能当作可评测成功实验")
    dataset, protocol = read_json(dataset_path), read_json(protocol_path)
    audit(dataset)
    if not isinstance(protocol, dict):
        raise ValueError("评测协议必须为对象")
    if digest(dataset) != run["dataset_id"]:
        raise ValueError("评测真值的数据版本与实验不一致")
    predictions = read_json(record_path.parent / "predictions.json")
    if predictions.get("dataset_id") != run["dataset_id"]:
        raise ValueError("预测没有绑定正确数据版本")
    task = dataset["task"]
    module = {"detection": detection, "pointcloud": pointcloud, "video-action": video}[task]
    key = {"detection": "iou_threshold", "pointcloud": "distance_threshold_m", "video-action": "event_iou_threshold"}[task]
    threshold = number(protocol.get(key), key, 0.0000001, 1 if task != "pointcloud" else None)
    if protocol.get("split") not in {"train", "validation", "test"}:
        raise ValueError("评测协议必须声明 split")
    selected = [s for s in dataset["samples"] if s["split"] == protocol["split"]]
    if not selected:
        raise ValueError("评测集合无样本")
    truth_by_id = {s["id"]: s for s in dataset["samples"]}
    pred_by_id = {}
    for sample in predictions["samples"]:
        if not isinstance(sample, dict):
            raise ValueError("预测样本必须为对象")
        sid = sample.get("id")
        if sid not in truth_by_id or sid in pred_by_id or not isinstance(sample.get("predictions"), list):
            raise ValueError("预测样本 ID 重复、未知或格式错误")
        pred_by_id[sid] = sample["predictions"]
    counts, slices, errors, bindings, details, class_counts = {"tp": 0, "fp": 0, "fn": 0}, {}, [], [], [], {}
    for sample in selected:
        predicted, truth = pred_by_id.get(sample["id"], []), sample["ground_truth"]
        for item in [*predicted, *truth]:
            if not isinstance(item, dict) or not isinstance(item.get("label"), str) or not item["label"]:
                raise ValueError("预测和真值必须声明类别")
            module.validate(item)
        pairs = match(predicted, truth, lambda p, g: module.cost(p, g, threshold))
        local = {"tp": len(pairs), "fp": len(predicted) - len(pairs), "fn": len(truth) - len(pairs)}
        for key in counts:
            counts[key] += local[key]
        bucket = slices.setdefault(sample.get("slice", "unspecified"), {"tp": 0, "fp": 0, "fn": 0, "samples": 0})
        bucket["samples"] += 1
        for key in counts:
            bucket[key] += local[key]
        matched_p, matched_g = {p for p, _ in pairs}, {g for _, g in pairs}
        for label in {x["label"] for x in [*predicted, *truth]}:
            bucket_class = class_counts.setdefault(label, {"tp": 0, "fp": 0, "fn": 0})
            bucket_class["tp"] += sum(predicted[p]["label"] == label for p, _ in pairs)
            bucket_class["fp"] += sum(x["label"] == label and p not in matched_p for p, x in enumerate(predicted))
            bucket_class["fn"] += sum(x["label"] == label and g not in matched_g for g, x in enumerate(truth))
        if task == "pointcloud":
            errors.extend(pointcloud.distance(predicted[p], truth[g]) for p, g in pairs)
        if task == "video-action":
            bindings.extend(video.bound(p, sample["id"]) for p in predicted)
        if (sample["id"] not in pred_by_id or local["fp"] or local["fn"]
                or task == "video-action" and any(not video.bound(p, sample["id"]) for p in predicted)):
            details.append({"sample_id": sample["id"], **local, "matched": pairs,
                            "predictions_missing": sample["id"] not in pred_by_id})
    metrics = {**counts, **ratios(counts)}
    if task == "pointcloud":
        metrics.update(center_error_mean_m=sum(errors) / len(errors) if errors else None,
                       center_error_max_m=max(errors) if errors else None)
    if task == "video-action":
        metrics["evidence_binding"] = sum(bindings) / len(bindings) if bindings else None
    performance_path = record_path.parent / "performance.json"
    # Only hash-bound traces can contribute to a report. The reader never accepts runner scores.
    performance = read_json(performance_path) if "performance.json" in run["artifact_hashes"] else {}
    edge.compute(performance, list(truth_by_id))
    selected_ids = {s["id"] for s in selected}
    selected_performance = {**performance, "traces": [t for t in performance.get("traces", []) if t["sample_id"] in selected_ids]}
    metrics.update(edge.compute(selected_performance, selected_ids))
    metrics["missing_prediction_samples"] = len(selected_ids - set(pred_by_id))
    negative_samples = [s for s in selected if not s["ground_truth"]]
    metrics["false_positive_sample_rate"] = (sum(bool(pred_by_id.get(s["id"])) for s in negative_samples)
                                               / len(negative_samples) if negative_samples else None)
    if metrics["failure_rate"] is not None:
        metrics["failure_rate"] = max(metrics["failure_rate"], metrics["missing_prediction_samples"] / len(selected_ids))
    coverage = {"samples": len(selected), "negative_samples": len(negative_samples),
                "predicted_samples": len(selected_ids & set(pred_by_id))}
    checks = [{"metric": "missing_prediction_samples", "kind": "max", "limit": 0,
               "observed": metrics["missing_prediction_samples"], "passed": metrics["missing_prediction_samples"] == 0}]
    for key, observed in (("minimum_samples", len(selected)), ("minimum_negative_samples", len(negative_samples))):
        limit = protocol.get(key, 1)
        if type(limit) is not int or limit < 1:
            raise ValueError(f"{key} 必须为正整数")
        checks.append({"metric": key, "kind": "min", "limit": limit, "observed": observed, "passed": observed >= limit})
    available = {"precision", "recall", "evidence_binding", "center_error_mean_m", "center_error_max_m", "p95_latency_ms", "failure_rate", "false_positive_sample_rate"}
    required_by_task = protocol.get("required_metrics", {})
    if not isinstance(required_by_task, dict):
        raise ValueError("required_metrics 必须按任务声明")
    required = required_by_task.get(task, [])
    if not isinstance(required, list) or not required or set(required) - available:
        raise ValueError("required_metrics 缺失或未知")
    for metric in required:
        checks.append({"metric": metric, "kind": "required", "passed": metrics.get(metric) is not None})
    thresholds = protocol.get("thresholds", {})
    if not isinstance(thresholds, dict) or not thresholds:
        raise ValueError("评测不能使用空验收门槛")
    for name, limit in thresholds.items():
        if name.endswith("_min"):
            metric, relation = name[:-4], "min"
        elif name.endswith("_max"):
            metric, relation = name[:-4], "max"
        else:
            raise ValueError(f"未知阈值操作: {name}")
        if metric not in available:
            raise ValueError(f"未知评测指标: {metric}")
        number(limit, name, 0, 1 if metric in {"precision", "recall", "evidence_binding", "failure_rate", "false_positive_sample_rate"} else None)
        if metric not in metrics and metric not in required:
            continue  # The shared protocol can carry thresholds for other task types.
        value = metrics.get(metric)
        passed = value is not None and (value >= limit if relation == "min" else value <= limit)
        checks.append({"metric": metric, "kind": relation, "limit": limit, "observed": value, "passed": passed})
    constrained = {c["metric"] for c in checks if c["kind"] != "required"}
    if not {"precision", "recall"}.issubset(constrained):
        raise ValueError("验收协议必须约束 precision 和 recall")
    verdict = "PASS" if all(c["passed"] for c in checks) else "FAIL"
    report_id = "eval-" + uuid.uuid4().hex
    report = {"schema_version": 1, "report_id": report_id, "created_at": stamp(), "run_id": run["run_id"],
              "run_record_hash": run["record_hash"], "dataset_id": run["dataset_id"], "task": task,
              "protocol": protocol, "protocol_hash": digest(protocol),
              "prediction_hash": file_hash(record_path.parent / "predictions.json"),
              "evaluator_hashes": {p.relative_to(ENGINE).as_posix(): file_hash(p) for p in ENGINE.rglob("*.py")},
              "evidence_level": dataset["evidence_level"], "split": protocol["split"], "samples": len(selected),
              "coverage": coverage, "not_evaluated": sorted(k for k in available if k in metrics and metrics[k] is None),
              "provenance": {"config_hash": run["config_hash"], "code_version": read_json(record_path.parent / "config.json")["code_version"],
                             "runner": run["runner"], "model": run["model"], "produced_models": run.get("produced_models", []),
                             "command": run["command"], "run_record": str(record_path)},
              "metrics": metrics, "slices": {k: {**v, **ratios(v)} for k, v in slices.items()},
              "classes": {k: {**v, **ratios(v)} for k, v in class_counts.items()}, "checks": checks,
              "failure_cases": details, "verdict": verdict, "production_authorized": False, "loading_authorized": False,
              "limitations": ["检测为固定阈值一对一匹配，不是 mAP。", "事件证据绑定只验证来源引用/时间/对象字段，不验证物理完成。",
                              "几何指标只覆盖匹配目标的中心误差；配组拓扑和实物尺寸尚未实现。",
                              "性能来自哈希绑定的 runner trace；不是独立硬件采样或长稳资格。",
                              "切片揭示域差异，不证明未见工位泛化；无现场授权。"]}
    report["report_hash"] = digest(report)
    target = guard_workspace(store) / "evaluations" / report_id
    save_json(target / "report.json", report, exclusive=True)
    lines = [f"# 独立评测 {report_id}", f"结论：{verdict}；证据等级：{dataset['evidence_level']}；生产授权：false。",
             f"实验：{run['run_id']}；数据：{run['dataset_id']}；协议：{digest(protocol)}。",
             "## 指标与覆盖", "```json", json.dumps({"metrics": metrics, "coverage": coverage, "not_evaluated": report["not_evaluated"]}, ensure_ascii=False, indent=2), "```",
             "## 验收检查", "```json", json.dumps(checks, ensure_ascii=False, indent=2), "```",
             "## 失败样本", "```json", json.dumps(details, ensure_ascii=False, indent=2), "```",
             "## 局限", *["- " + x for x in report["limitations"]]]
    (target / "report.md").write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    return {"report": str(target / "report.json"), "verdict": verdict, "metrics": metrics}


def compare(baseline, candidate):
    reports = []
    for path in (baseline, candidate):
        report = read_json(path)
        expected = report.pop("report_hash", None)
        if digest(report) != expected:
            raise ValueError("评测报告被修改")
        reports.append(report)
    before, after = reports
    for key in ("dataset_id", "protocol_hash", "task", "split"):
        if before[key] != after[key]:
            raise ValueError(f"不可比的评测: {key}")
    delta = {key: after["metrics"][key] - value for key, value in before["metrics"].items()
             if isinstance(value, (int, float)) and isinstance(after["metrics"].get(key), (int, float))}
    return {"baseline": before["report_id"], "candidate": after["report_id"], "delta": delta,
            "verdicts": [before["verdict"], after["verdict"]], "production_authorized": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="独立计算固定阈值检测、点云、事件和 trace 性能指标")
    parser.add_argument("--run", type=Path)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--store", type=Path, default=ROOT / "local/experiments")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.baseline and args.candidate:
            result = compare(args.baseline, args.candidate)
        elif args.run and args.dataset and args.protocol:
            result = evaluate(args.run, args.dataset, args.protocol, args.store)
        else:
            raise ValueError("提供 --run --dataset --protocol 或 --baseline --candidate")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("verdict") == "FAIL" else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
