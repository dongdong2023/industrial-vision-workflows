"""A standard-library calibration training example, using train labels only."""
import argparse
import json
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--input", type=Path, required=True)
parser.add_argument("--config", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
inputs = json.loads(args.input.read_text(encoding="utf-8"))
config = json.loads(args.config.read_text(encoding="utf-8"))
offsets = []
for sample in inputs["samples"]:
    if sample["split"] == "train":
        observed, truth = sample["observations"], sample["ground_truth"]
        if len(observed) == len(truth) == 1 and observed[0]["label"] == truth[0]["label"]:
            offsets.append([truth[0]["center"][axis] - observed[0]["center"][axis] for axis in range(3)])
if not offsets:
    raise ValueError("training requires labeled train groups")
bias = [sum(x[axis] for x in offsets) / len(offsets) for axis in range(3)] if config["parameters"]["calibrate"] else [0, 0, 0]
model = {"id": "synthetic-calibration", "version": "1", "bias_xyz_m": bias, "training_samples": len(offsets)}
(args.output / "calibration-model.json").write_text(json.dumps(model, indent=2), encoding="utf-8")
(args.output / "models.json").write_text(json.dumps({"models": [{"id": model["id"], "version": "1", "path": "calibration-model.json"}]}), encoding="utf-8")
samples, traces = [], []
for sample in inputs["samples"]:
    start = time.perf_counter()
    predicted = [{**item, "center": [item["center"][axis] + bias[axis] for axis in range(3)]} for item in sample["observations"]]
    samples.append({"id": sample["id"], "predictions": predicted})
    traces.append({"sample_id": sample["id"], "latency_ms": (time.perf_counter() - start) * 1000, "ok": True})
(args.output / "predictions.json").write_text(json.dumps({"dataset_id": inputs["dataset_id"], "samples": samples}, indent=2), encoding="utf-8")
(args.output / "performance.json").write_text(json.dumps({"source": "synthetic-calibration-process", "hardware": "local-cpu", "traces": traces}), encoding="utf-8")
print("trained calibration on", len(offsets), "train groups; inferred", len(samples), "samples")
