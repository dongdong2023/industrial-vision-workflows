import importlib.util
import itertools
import math
import random
import sys
import unittest
from pathlib import Path

from ivw.common import ROOT


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


matching = load("test_matching", "engines/evaluation-engine/reporting/matching.py")
detection = load("test_detection", "engines/evaluation-engine/detection/metrics.py")
video = load("test_video", "engines/evaluation-engine/video-action/metrics.py")
edge = load("test_edge", "engines/evaluation-engine/edge-performance/metrics.py")


class MetricTests(unittest.TestCase):
    def test_matching_avoids_greedy_false_negative(self):
        edges = [[0.1, 0.2], [0.11, None]]
        pairs = matching.match([0, 1], [0, 1], lambda a, b: edges[a][b])
        self.assertEqual(set(pairs), {(0, 1), (1, 0)})

    def test_matching_matches_exhaustive_optimum(self):
        rng = random.Random(7)
        for _ in range(30):
            edges = [[None if rng.random() < 0.3 else rng.random() for _ in range(3)] for _ in range(3)]
            pairs = matching.match(list(range(3)), list(range(3)), lambda a, b: edges[a][b])
            actual = (-len(pairs), sum(edges[a][b] for a, b in pairs))
            candidates = []
            for assignment in itertools.product(range(-1, 3), repeat=3):
                used = [b for b in assignment if b >= 0]
                if len(used) != len(set(used)) or any(b >= 0 and edges[a][b] is None for a, b in enumerate(assignment)):
                    continue
                candidates.append((-len(used), sum(edges[a][b] for a, b in enumerate(assignment) if b >= 0)))
            expected = min(candidates)
            self.assertEqual(actual[0], expected[0])
            self.assertAlmostEqual(actual[1], expected[1])

    def test_duplicate_predictions_cannot_inflate_tp(self):
        box = {"label": "part", "box": [0, 0, 1, 1]}
        self.assertEqual(len(matching.match([box, box], [box], lambda a, b: detection.cost(a, b, 0.5))), 1)

    def test_invalid_boxes_and_times_rejected(self):
        for box in ([1, 0, 0, 1], [0, 0, float("nan"), 1], [0, 0, 2, 1]):
            with self.assertRaises(ValueError):
                detection.validate({"box": box})
        with self.assertRaises(ValueError):
            video.validate({"start": 2, "end": 1})

    def test_evidence_references_fail_closed(self):
        event = {"start": 1, "end": 2, "evidence": {"sample_id": "sample", "object_id": "part", "time": 1.5}}
        self.assertTrue(video.bound(event, "sample"))
        self.assertFalse(video.bound(event, "other"))
        event["evidence"]["time"] = 3
        self.assertFalse(video.bound(event, "sample"))
        event["evidence"] = None
        self.assertFalse(video.bound(event, "sample"))

    def test_performance_tail_and_failures(self):
        data = {"traces": [{"sample_id": str(i), "latency_ms": i + 1, "ok": i != 19} for i in range(20)]}
        result = edge.compute(data, [str(i) for i in range(20)])
        self.assertEqual(result, {"p95_latency_ms": 19, "failure_rate": 0.05})
        data["traces"].pop()
        with self.assertRaises(ValueError):
            edge.compute(data, [str(i) for i in range(20)])

    def test_no_performance_trace_is_unknown(self):
        self.assertIsNone(edge.compute({}, ["sample"])["p95_latency_ms"])

    def test_malformed_trace_is_an_error(self):
        for data in ([], {"traces": "bad"}, {"traces": [None]}):
            with self.assertRaises(ValueError):
                edge.compute(data, ["sample"])


if __name__ == "__main__":
    unittest.main()
