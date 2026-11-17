"""A real local process operating on synthetic observations, never annotations."""
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
threshold = config["parameters"]["min_score"]
if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
    raise ValueError("min_score outside [0,1]")
samples, traces = [], []
for sample in inputs["samples"]:
    start = time.perf_counter()
    predictions = [dict(item) for item in sample["observations"] if item["score"] >= threshold]
    samples.append({"id": sample["id"], "predictions": predictions})
    traces.append({"sample_id": sample["id"], "latency_ms": (time.perf_counter() - start) * 1000, "ok": True})
(args.output / "predictions.json").write_text(json.dumps({"dataset_id": inputs["dataset_id"], "samples": samples}, indent=2), encoding="utf-8")
(args.output / "performance.json").write_text(json.dumps({"source": "synthetic-observer-process", "hardware": "local-cpu", "traces": traces}, indent=2), encoding="utf-8")
print("synthetic observations processed:", len(samples))
