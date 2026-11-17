"""Experiment execution API. The caller owns workflow and approval decisions."""
import argparse
import json
import platform
import sys
import traceback
import uuid
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
ROOT = ENGINE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ENGINE))
from ivw.common import digest, file_hash, guard_workspace, number, read_json, runtime_env, save_json, stamp
from dataset.manifest import audit, register as register_dataset
from registry.runners import register as register_runner, resolve
from runners.process import execute
from tracking.records import load_run


def run(config_path, store):
    store = guard_workspace(store)
    config_path = Path(config_path).resolve()
    config = read_json(config_path)
    if not isinstance(config, dict) or not isinstance(config.get("parameters"), dict) or type(config.get("seed")) is not int:
        raise ValueError("实验必须有 parameters 与整数 seed")
    if not isinstance(config.get("code_version"), str) or not config["code_version"].strip():
        raise ValueError("实验必须固定 code_version")
    dataset_path = (config_path.parent / config["dataset"]).resolve()
    dataset = read_json(dataset_path)
    audit(dataset)
    registered = register_dataset(dataset_path, store)
    runner = resolve(config["runner"], store)
    timeout = number(config.get("timeout_seconds", 600), "timeout_seconds", 0.05, 86400)
    model = dict(config.get("model", {}))
    if not model.get("id") or not model.get("version"):
        raise ValueError("必须固定模型 id/version")
    if model.get("weights"):
        weights = (config_path.parent / model["weights"]).resolve()
        model.update(weights=str(weights), weights_sha256=file_hash(weights))
    run_id = "run-" + uuid.uuid4().hex
    output = store / "runs" / run_id
    output.mkdir(parents=True, exist_ok=False)
    # Training labels are available only on the train split. Held-out annotations never enter runner inputs.
    inputs = {"dataset_id": registered["dataset_id"], "task": dataset["task"],
              "samples": [{k: s[k] for k in ("id", "group", "split", "slice", "observations") if k in s}
                          for s in dataset["samples"]]}
    for source, target in zip(dataset["samples"], inputs["samples"]):
        if source["split"] == "train":
            target["ground_truth"] = source["ground_truth"]
    save_json(output / "input.json", inputs, exclusive=True)
    save_json(output / "config.json", config, exclusive=True)
    # Resolve model references for runners whose isolated cwd is not the config directory.
    save_json(output / "runner-config.json", {**config, "model": model}, exclusive=True)
    argv = [sys.executable, runner["file"], "--input", str(output / "input.json"),
            "--config", str(output / "runner-config.json"), "--output", str(output)]
    record = {"schema_version": 1, "run_id": run_id, "name": config["name"], "started_at": stamp(),
              "dataset_id": registered["dataset_id"], "dataset_path": registered["path"],
              "evidence_level": dataset["evidence_level"], "task": dataset["task"], "config_hash": digest(config),
              "runner": runner, "model": model, "command": argv, "python": platform.python_version(),
              "status": "failed", "loading_authorized": False, "production_authorized": False}
    try:
        process = execute(argv, output, runtime_env(), timeout)
        record.update(process)
        if process["timed_out"]:
            record["status"] = "timeout"
        elif process["returncode"] == 0:
            predictions = read_json(output / "predictions.json")
            if predictions.get("dataset_id") != registered["dataset_id"] or not isinstance(predictions.get("samples"), list):
                raise ValueError("runner 预测未绑定数据版本或格式错误")
            record["status"] = "completed"
        if file_hash(runner["file"]) != runner["sha256"]:
            raise ValueError("runner 在执行期间被修改")
        if model.get("weights") and file_hash(model["weights"]) != model["weights_sha256"]:
            raise ValueError("模型权重在执行期间被修改")
        if (digest(read_json(output / "config.json")) != record["config_hash"] or read_json(output / "input.json") != inputs
                or read_json(output / "runner-config.json") != {**config, "model": model}):
            raise ValueError("runner 修改了固定输入或配置")
    except Exception as exc:
        record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        (output / "engine-error.log").write_text(traceback.format_exc(), encoding="utf-8")
    record["produced_models"] = []
    try:
        model_manifest = output / "models.json"
        if record["status"] == "completed" and model_manifest.exists():
            from ivw.common import child, identifier
            for model_item in read_json(model_manifest)["models"]:
                identifier(model_item["id"])
                identifier(model_item["version"])
                artifact = child(output, model_item["path"])
                if not artifact.is_file() or artifact.is_symlink():
                    raise ValueError("模型产物缺失或为链接")
                produced = {"id": model_item["id"], "version": model_item["version"],
                            "path": str(artifact), "sha256": file_hash(artifact),
                            "run_id": run_id, "dataset_id": registered["dataset_id"], "config_hash": digest(config)}
                save_json(store / "models" / model_item["id"] / (run_id + ".json"), produced, exclusive=True)
                record["produced_models"].append(produced)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        record.update(status="failed", error=f"model registration: {exc}")
    record["finished_at"] = stamp()
    record["artifact_hashes"] = {}
    for path in sorted(output.rglob("*")):
        if path.is_symlink():
            record.update(status="failed", error="runner 输出不允许符号链接")
            continue
        if path.is_file():
            record["artifact_hashes"][path.relative_to(output).as_posix()] = file_hash(path)
    record["record_hash"] = digest(record)
    save_json(output / "run.json", record, exclusive=True)
    return {"run_id": run_id, "record": str(output / "run.json"), "status": record["status"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="执行与管理工业视觉实验（标准库）")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("dataset", "register-runner", "run", "failure", "compare"):
        p = sub.add_parser(name)
        p.add_argument("--store", type=Path, default=ROOT / "local/experiments")
        if name in {"dataset", "failure", "register-runner"}:
            p.add_argument("--file", type=Path, required=True)
        if name == "register-runner":
            p.add_argument("--name", required=True)
        if name == "run":
            p.add_argument("--config", type=Path, required=True)
        if name == "compare":
            p.add_argument("--baseline", type=Path, required=True)
            p.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        guard_workspace(args.store)
        if args.command == "dataset":
            result = register_dataset(args.file, args.store)
        elif args.command == "register-runner":
            result = register_runner(args.name, args.file, args.store)
        elif args.command == "run":
            result = run(args.config, args.store)
        elif args.command == "failure":
            case = read_json(args.file)
            if any(not case.get(k) for k in ("sample_id", "stage", "expected", "observed", "hypothesis", "evidence_level")):
                raise ValueError("失败案例缺少必要字段")
            case_id = "failure-" + uuid.uuid4().hex
            save_json(args.store / "failures" / (case_id + ".json"), {"id": case_id, "created_at": stamp(), **case}, exclusive=True)
            result = {"failure_id": case_id}
        else:
            before, after = load_run(args.baseline), load_run(args.candidate)
            if before["dataset_id"] != after["dataset_id"] or before["task"] != after["task"]:
                raise ValueError("不能对比不同数据版本或任务")
            result = {"baseline": before["run_id"], "candidate": after["run_id"],
                      "same_runner": before["runner"]["sha256"] == after["runner"]["sha256"],
                      "config_changed": before["config_hash"] != after["config_hash"],
                      "status": [before["status"], after["status"]], "note": "效果比较必须使用独立 Evaluation Engine"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if isinstance(result.get("status"), str) and result["status"] in {"failed", "timeout"} else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
