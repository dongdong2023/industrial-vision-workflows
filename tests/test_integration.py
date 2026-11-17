import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ivw import integration
from ivw.cli import validate
from ivw.common import ROOT, child, file_hash, guard_workspace, guard_write, read_json, runtime_env, save_json


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / "local/test-runs"
        base.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(dir=base)
        cls.root = Path(cls.temp.name).resolve()
        assert cls.root.is_relative_to(base.resolve())
        cls.addClassCleanup(cls.temp.cleanup)

    def test_component_contracts_and_unmodified_upstream(self):
        result = validate()
        self.assertEqual((result["profiles"], result["skills"], result["workflows"], result["checks"]), (3, 7, 4, 10))
        self.assertGreater(result["files_verified"], 100)

    def test_protected_roots_and_ancestors_rejected(self):
        for source in read_json(ROOT / "config/protection.json")["read_only_roots"]:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    guard_write(Path(source) / "must-not-write.json")
                with self.assertRaises(ValueError):
                    guard_workspace(Path(source).parent)
        with self.assertRaises(ValueError):
            integration.install(ROOT / "vendor/loopforge/must-not-create")

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            child(self.root, "../outside.txt")
        with self.assertRaises(ValueError):
            child(self.root, "inside/../file.txt")

    def test_uninstall_rejects_traversal_in_install_manifest(self):
        workspace = self.root / "tampered-manifest"
        target = workspace / "user.txt"
        target.parent.mkdir(parents=True)
        target.write_text("keep", encoding="utf-8")
        save_json(workspace / ".ivw/install.json", {"files": {".agents/skills/vision-x/../../../user.txt": file_hash(target)}})
        with self.assertRaises(ValueError):
            integration.uninstall(workspace)
        self.assertEqual(target.read_text(), "keep")

    def test_profile_mismatch_and_unknown_check_rejected(self):
        with self.assertRaises(ValueError):
            integration.inspect("sop-product", "sop-model-research")
        with self.assertRaises(ValueError):
            integration.inspect("sop-research", "sop-model-research", ["missing-check"])

    def test_native_install_all_workflow_prompts_and_gate(self):
        workspace = self.root / "portable 中文 path"
        integration.install(workspace)
        status = json.loads(integration.upstream(["skills", "status", "codex", "--project-root", workspace, "--json"]))
        self.assertEqual(status[0]["changed"], 0)
        self.assertEqual(status[0]["missing"], 0)
        for path in (ROOT / "workflows").glob("*/workflow.json"):
            spec = read_json(path)
            initialized = integration.init_workflow(workspace, spec["id"], spec["profile"], spec["id"])
            state = initialized["state"]
            generated = integration.prepare(state, "REQUIREMENT", "独立离线验证")
            prompt = Path(generated["prompt"]).read_text(encoding="utf-8")
            self.assertIn(spec["id"], prompt)
            self.assertIn(spec["profile"], prompt)
            self.assertIn("vision-dataset-audit", prompt)
            script = integration.workflow_script(workspace)
            result = subprocess.run([sys.executable, str(script), "start", "--state", state, "--stage", "DESIGN"],
                                    capture_output=True, env=runtime_env())
            self.assertNotEqual(result.returncode, 0)
            result = subprocess.run([sys.executable, str(script), "approve", "--state", state, "--stage", "REQUIREMENT"],
                                    capture_output=True, env=runtime_env())
            self.assertNotEqual(result.returncode, 0)
            integration.command([sys.executable, str(script), "validate", "--state", state])

    def test_install_conflict_preflight_preserves_existing_file(self):
        workspace = self.root / "conflict"
        target = workspace / ".agents/skills/vision-project-intake/SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("user-owned", encoding="utf-8")
        with self.assertRaises(ValueError):
            integration.install(workspace)
        self.assertEqual(target.read_text(), "user-owned")
        self.assertFalse((workspace / ".devflow").exists())

    def test_native_user_edits_are_not_overwritten_on_reinstall(self):
        workspace = self.root / "native-edit"
        integration.install(workspace)
        target = workspace / ".agents/skills/devflow/SKILL.md"
        target.write_text("user-owned native skill", encoding="utf-8")
        with self.assertRaises(ValueError):
            integration.install(workspace)
        self.assertEqual(target.read_text(), "user-owned native skill")

    def test_init_cli_accepts_read_only_project_example(self):
        workspace = self.root / "example-cli"
        integration.install(workspace)
        output = integration.command([sys.executable, str(ROOT / "ivw.py"), "init", "--project", str(workspace),
                                      "--slug", "example", "--profile", "sop-research", "--workflow", "sop-model-research",
                                      "--example", "sop"])
        initialized = json.loads(output)
        context = read_json(Path(initialized["state"]).parent / "industrial/context.json")
        self.assertEqual(context["project_source"]["source_read_only"], read_json(ROOT / "examples/projects/sop.json")["source_root"])

    def test_uninstall_keeps_user_edits_and_experiment_outputs(self):
        workspace = self.root / "uninstall"
        integration.install(workspace)
        target = workspace / ".agents/skills/vision-error-analysis/SKILL.md"
        target.write_text("user-edited", encoding="utf-8")
        output = workspace / "artifacts/keep.txt"
        output.parent.mkdir()
        output.write_text("keep", encoding="utf-8")
        result = integration.uninstall(workspace)
        self.assertIn(".agents/skills/vision-error-analysis/SKILL.md", result["preserved"])
        self.assertEqual(target.read_text(), "user-edited")
        self.assertEqual(output.read_text(), "keep")
        self.assertFalse((workspace / ".agents/skills/vision-project-intake/SKILL.md").exists())

    def test_read_only_examples_contain_hashed_sources(self):
        for name in ("sop", "saddles"):
            result = integration.project_context(name, self.root / (name + ".md"))
            self.assertTrue(result["evidence"])
            self.assertTrue(all(len(x["sha256"]) == 64 for x in result["evidence"]))


if __name__ == "__main__":
    unittest.main()
