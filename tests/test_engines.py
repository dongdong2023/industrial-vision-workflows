import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ivw.common import ROOT, digest, read_json, runtime_env, save_json


class EngineTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "local/test-runs"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(base.resolve())
        self.addCleanup(self.temp.cleanup)

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, str(ROOT / "ivw.py"), *map(str, args)], capture_output=True,
                                text=True, encoding="utf-8", env=runtime_env(), cwd=ROOT)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else result.stderr

    def run_example(self, task="sop", variant="baseline"):
        return self.cli("experiment", "run", "--config", ROOT / f"examples/experiments/{task}-{variant}.json", "--store", self.root)

    def evaluate(self, run, task="sop", code=0, dataset=None, protocol=None):
        return self.cli("evaluate", "--run", run["record"], "--dataset", dataset or ROOT / f"examples/datasets/{task}.json",
                        "--protocol", protocol or ROOT / "examples/evaluation-protocol.json", "--store", self.root, code=code)

    def test_actual_runner_and_independent_event_metrics(self):
        run = self.run_example()
        record = read_json(run["record"])
        self.assertEqual(record["returncode"], 0)
        self.assertGreater(record["wall_seconds"], 0)
        self.assertTrue((Path(run["record"]).parent / "stdout.log").read_text().strip())
        self.assertTrue(all("ground_truth" not in s for s in read_json(Path(run["record"]).parent / "input.json")["samples"]))
        report = self.evaluate(run)
        self.assertEqual((report["metrics"]["tp"], report["metrics"]["fp"], report["metrics"]["fn"]), (4, 0, 1))
        self.assertEqual(report["metrics"]["recall"], 0.8)
        self.assertFalse(read_json(report["report"])["production_authorized"])

    def test_more_events_can_fail_evidence_binding(self):
        report = self.evaluate(self.run_example(variant="candidate"), code=1)
        self.assertEqual(report["metrics"]["recall"], 1)
        self.assertEqual(report["metrics"]["evidence_binding"], 0.8)
        self.assertEqual(report["verdict"], "FAIL")

    def test_false_positive_is_not_hidden(self):
        report = self.evaluate(self.run_example("detection", "candidate"), "detection")
        self.assertEqual(report["metrics"]["fp"], 1)
        self.assertEqual(report["metrics"]["precision"], 0.8)
        self.assertEqual(read_json(report["report"])["classes"]["part"]["fp"], 1)

    def test_geometry_error_causes_fp_and_fn(self):
        report = self.evaluate(self.run_example("saddles"), "saddles", code=1)
        self.assertEqual((report["metrics"]["tp"], report["metrics"]["fp"], report["metrics"]["fn"]), (3, 1, 2))
        self.assertAlmostEqual(report["metrics"]["center_error_max_m"], 0.03)

    def test_training_registers_model_and_held_out_improvement(self):
        before = self.run_example("calibration")
        after = self.run_example("calibration", "candidate")
        record = read_json(after["record"])
        self.assertEqual(len(record["produced_models"]), 1)
        inputs = read_json(Path(after["record"]).parent / "input.json")["samples"]
        self.assertTrue(all(("ground_truth" in x) == (x["split"] == "train") for x in inputs))
        self.assertTrue(list((self.root / "models/synthetic-calibration").glob("*.json")))
        first = self.evaluate(before, "calibration", code=1)
        second = self.evaluate(after, "calibration")
        self.assertAlmostEqual(first["metrics"]["center_error_max_m"], 0.12)
        self.assertLess(second["metrics"]["center_error_max_m"], 1e-12)
        diff = self.cli("evaluate", "--baseline", first["report"], "--candidate", second["report"])
        self.assertLess(diff["delta"]["center_error_max_m"], -0.1)

    def test_tampered_predictions_rejected(self):
        run = self.run_example()
        (Path(run["record"]).parent / "predictions.json").write_text("{}")
        self.evaluate(run, code=2)

    def test_tampered_record_rejected(self):
        run = self.run_example()
        record = read_json(run["record"])
        record["status"] = "approved"
        save_json(run["record"], record)
        self.evaluate(run, code=2)

    def test_wrong_ground_truth_version_rejected(self):
        run = self.run_example()
        data = read_json(ROOT / "examples/datasets/sop.json")
        data["samples"][0]["ground_truth"] = []
        save_json(self.root / "changed.json", data)
        self.evaluate(run, dataset=self.root / "changed.json", code=2)

    def test_group_leakage_rejected(self):
        data = read_json(ROOT / "examples/datasets/sop.json")
        data["samples"][1].update(group=data["samples"][0]["group"], split="train")
        save_json(self.root / "bad.json", data)
        self.cli("experiment", "dataset", "--file", self.root / "bad.json", "--store", self.root, code=2)

    def test_raw_content_leakage_rejected(self):
        data = read_json(ROOT / "examples/datasets/sop.json")
        data["samples"][0]["content_sha256"] = "a" * 64
        data["samples"][1].update(content_sha256="a" * 64, split="train")
        save_json(self.root / "bad.json", data)
        self.cli("experiment", "dataset", "--file", self.root / "bad.json", "--store", self.root, code=2)

    def test_dataset_duplicate_ids_rejected(self):
        data = read_json(ROOT / "examples/datasets/sop.json")
        data["samples"][1]["id"] = data["samples"][0]["id"]
        save_json(self.root / "bad.json", data)
        self.cli("experiment", "dataset", "--file", self.root / "bad.json", "--store", self.root, code=2)

    def custom_config(self, script, timeout=5):
        path = self.root / "runner.py"
        path.write_text(script, encoding="utf-8")
        self.cli("experiment", "register-runner", "--name", "local-test", "--file", path, "--store", self.root)
        config = read_json(ROOT / "examples/experiments/sop-baseline.json")
        config.update(runner="local-test", dataset=str(ROOT / "examples/datasets/sop.json"), timeout_seconds=timeout)
        save_json(self.root / "config.json", config)
        return self.root / "config.json"

    def test_failed_process_is_recorded_and_not_evaluated(self):
        config = self.custom_config("raise RuntimeError('deliberate test failure')\n")
        run = self.cli("experiment", "run", "--config", config, "--store", self.root, code=1)
        self.assertEqual(run["status"], "failed")
        self.assertIn("deliberate test failure", (Path(run["record"]).parent / "stderr.log").read_text())
        self.evaluate(run, code=2)

    def test_timeout_is_preserved(self):
        config = self.custom_config("import time\ntime.sleep(5)\n", timeout=0.1)
        run = self.cli("experiment", "run", "--config", config, "--store", self.root, code=1)
        self.assertEqual(run["status"], "timeout")
        self.assertTrue(read_json(run["record"])["timed_out"])

    def test_runner_changed_after_registration_rejected(self):
        config = self.custom_config("print('initial')\n")
        (self.root / "runner.py").write_text("print('changed')\n")
        self.cli("experiment", "run", "--config", config, "--store", self.root, code=2)

    def test_run_ids_unique_and_failure_cases_append(self):
        first, second = self.run_example(), self.run_example()
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertTrue(Path(first["record"]).is_file())
        for _ in range(2):
            self.cli("experiment", "failure", "--file", ROOT / "examples/failure-case.json", "--store", self.root)
        self.assertEqual(len(list((self.root / "failures").glob("*.json"))), 2)

    def test_experiment_comparison_requires_same_dataset(self):
        first, second = self.run_example(), self.run_example("saddles")
        self.cli("experiment", "compare", "--baseline", first["record"], "--candidate", second["record"], code=2)

    def test_report_comparison_requires_same_protocol(self):
        run = self.run_example()
        first = self.evaluate(run)
        protocol = read_json(ROOT / "examples/evaluation-protocol.json")
        protocol["thresholds"]["recall_min"] = 0.7
        save_json(self.root / "protocol.json", protocol)
        second = self.evaluate(run, protocol=self.root / "protocol.json")
        self.cli("evaluate", "--baseline", first["report"], "--candidate", second["report"], code=2)

    def test_unknown_metric_and_nan_rejected(self):
        run = self.run_example()
        protocol = read_json(ROOT / "examples/evaluation-protocol.json")
        protocol["thresholds"]["made_up_min"] = 0.2
        save_json(self.root / "protocol.json", protocol)
        self.evaluate(run, protocol=self.root / "protocol.json", code=2)
        protocol["thresholds"].pop("made_up_min")
        protocol["thresholds"]["recall_min"] = float("nan")
        (self.root / "protocol.json").write_text(json.dumps(protocol), encoding="utf-8")
        self.evaluate(run, protocol=self.root / "protocol.json", code=2)

    def test_malformed_protocol_rejected_as_input_error(self):
        run = self.run_example()
        for key, value in (("thresholds", ["recall_min"]), ("required_metrics", []), ("minimum_samples", True)):
            protocol = read_json(ROOT / "examples/evaluation-protocol.json")
            protocol[key] = value
            save_json(self.root / "malformed.json", protocol)
            self.evaluate(run, protocol=self.root / "malformed.json", code=2)

    def test_invalid_units_rejected(self):
        data = read_json(ROOT / "examples/datasets/saddles.json")
        data["coordinate_unit"] = "mm"
        save_json(self.root / "bad.json", data)
        self.cli("experiment", "dataset", "--file", self.root / "bad.json", "--store", self.root, code=2)

    def observer_with(self, extra):
        script = (ROOT / "examples/runners/synthetic_observer.py").read_text(encoding="utf-8")
        return self.custom_config(script + "\n" + extra + "\n")

    def test_missing_negative_prediction_fails_even_without_performance_gate(self):
        config = self.observer_with("""
path = args.output / 'predictions.json'
data = json.loads(path.read_text())
data['samples'] = [s for s in data['samples'] if s['id'] != 'sop-5']
path.write_text(json.dumps(data))
""")
        run = self.cli("experiment", "run", "--config", config, "--store", self.root)
        protocol = read_json(ROOT / "examples/evaluation-protocol.json")
        protocol["thresholds"]["failure_rate_max"] = 1
        save_json(self.root / "protocol.json", protocol)
        result = self.evaluate(run, protocol=self.root / "protocol.json", code=1)
        report = read_json(result["report"])
        self.assertEqual(result["metrics"]["missing_prediction_samples"], 1)
        self.assertTrue(any(c["predictions_missing"] and c["sample_id"] == "sop-5" for c in report["failure_cases"]))

    def test_runner_scores_cannot_override_independent_ground_truth(self):
        config = self.observer_with("""
path = args.output / 'predictions.json'
data = json.loads(path.read_text())
for sample in data['samples']:
    sample['predictions'] = []
path.write_text(json.dumps(data))
(args.output / 'metrics.json').write_text(json.dumps({'precision': 1, 'recall': 1}))
""")
        run = self.cli("experiment", "run", "--config", config, "--store", self.root)
        result = self.evaluate(run, code=1)
        self.assertEqual(result["metrics"]["recall"], 0)
        self.assertIsNone(result["metrics"]["precision"])

    def test_missing_trace_is_reported_unknown_and_fails_required_metric(self):
        config = self.observer_with("(args.output / 'performance.json').unlink()")
        run = self.cli("experiment", "run", "--config", config, "--store", self.root)
        result = self.evaluate(run, code=1)
        self.assertIsNone(result["metrics"]["p95_latency_ms"])
        self.assertIn("p95_latency_ms", read_json(result["report"])["not_evaluated"])

    def test_insufficient_samples_and_absent_negatives_cannot_pass(self):
        data = read_json(ROOT / "examples/datasets/sop.json")
        data["samples"] = [s for s in data["samples"] if s["ground_truth"]]
        save_json(self.root / "positive-only.json", data)
        config = read_json(ROOT / "examples/experiments/sop-baseline.json")
        config["dataset"] = str(self.root / "positive-only.json")
        save_json(self.root / "config.json", config)
        run = self.cli("experiment", "run", "--config", self.root / "config.json", "--store", self.root)
        result = self.evaluate(run, dataset=self.root / "positive-only.json", code=1)
        report = read_json(result["report"])
        self.assertEqual(report["coverage"]["negative_samples"], 0)
        self.assertTrue(any(c["metric"] == "minimum_negative_samples" and not c["passed"] for c in report["checks"]))
        protocol = read_json(ROOT / "examples/evaluation-protocol.json")
        protocol["minimum_samples"] = 100
        save_json(self.root / "protocol.json", protocol)
        result = self.evaluate(run, dataset=self.root / "positive-only.json", protocol=self.root / "protocol.json", code=1)
        self.assertTrue(any(c["metric"] == "minimum_samples" and not c["passed"] for c in read_json(result["report"])["checks"]))

    def test_unverified_annotation_cannot_become_negative(self):
        data = read_json(ROOT / "examples/datasets/sop.json")
        data["samples"][-1]["annotation_status"] = "unknown"
        save_json(self.root / "unknown.json", data)
        self.cli("experiment", "dataset", "--file", self.root / "unknown.json", "--store", self.root, code=2)

    def test_relative_model_reference_is_resolved_and_mutation_is_recorded(self):
        config_path = self.observer_with("""
weights = Path(config['model']['weights'])
assert weights.is_absolute() and weights.read_bytes() == b'original'
if config['parameters'].get('mutate_weights'):
    weights.write_bytes(b'changed')
""")
        (self.root / "weights.bin").write_bytes(b"original")
        config = read_json(config_path)
        config["model"]["weights"] = "weights.bin"
        save_json(config_path, config)
        self.cli("experiment", "run", "--config", config_path, "--store", self.root)
        config["parameters"]["mutate_weights"] = True
        save_json(config_path, config)
        failed = self.cli("experiment", "run", "--config", config_path, "--store", self.root, code=1)
        self.assertIn("模型权重", read_json(failed["record"])["error"])

    def test_runner_cannot_change_frozen_config(self):
        config = self.observer_with("(args.output / 'config.json').write_text('{}')")
        result = self.cli("experiment", "run", "--config", config, "--store", self.root, code=1)
        self.assertIn("固定输入或配置", read_json(result["record"])["error"])

    def test_completed_record_must_bind_predictions(self):
        run = self.run_example()
        record = read_json(run["record"])
        record["artifact_hashes"].pop("predictions.json")
        record.pop("record_hash")
        record["record_hash"] = digest(record)
        save_json(run["record"], record)
        self.evaluate(run, code=2)


if __name__ == "__main__":
    unittest.main()
