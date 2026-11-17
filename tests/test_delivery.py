import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from ivw.common import ROOT, read_json, runtime_env
from scripts import package


class DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / "local/test-runs"
        base.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(dir=base)
        cls.root = Path(cls.temp.name).resolve()
        assert cls.root.is_relative_to(base.resolve())
        cls.addClassCleanup(cls.temp.cleanup)
        cls.archive = cls.root / "delivery.zip"
        package.build(cls.archive)

    def test_archive_has_verified_sources_and_excludes_local_artifacts(self):
        with zipfile.ZipFile(self.archive) as archive:
            manifest = json.loads(archive.read("PACKAGE-MANIFEST.json"))
            self.assertEqual(set(archive.namelist()), {*manifest["files"], "PACKAGE-MANIFEST.json"})
            for name, expected in manifest["files"].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), expected)
                self.assertFalse(name.startswith(("local/", "workspaces/", ".agents/", ".ivw/", ".devflow/")))
                self.assertNotIn(Path(name).suffix, {".pt", ".onnx", ".mp4", ".pcd"})

    def test_relocated_package_validates_without_original_install_state(self):
        target = self.root / "解压 changed path"
        with zipfile.ZipFile(self.archive) as archive:
            archive.extractall(target)
        result = subprocess.run([sys.executable, str(target / "ivw.py"), "validate"], cwd=self.root,
                                capture_output=True, text=True, encoding="utf-8", env=runtime_env())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["workflows"], 4)

    def test_archive_cannot_overwrite_existing_delivery(self):
        before = self.archive.read_bytes()
        with self.assertRaises(FileExistsError):
            package.build(self.archive)
        self.assertEqual(self.archive.read_bytes(), before)

    def test_allowlist_rejects_local_records_and_weights(self):
        original = package.read_json
        for forbidden in ("local/experiments/run.json", "examples/private.pt", "../outside.md"):
            def changed(path):
                data = original(path)
                if Path(path).name == "share-files.json":
                    return {"files": [*data["files"], forbidden]}
                return data
            with self.subTest(path=forbidden), patch.object(package, "read_json", side_effect=changed):
                with self.assertRaises(ValueError):
                    package.build(self.root / "forbidden.zip")
                self.assertFalse((self.root / "forbidden.zip").exists())


if __name__ == "__main__":
    unittest.main()
