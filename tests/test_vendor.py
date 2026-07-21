from __future__ import annotations

import hashlib
import json
import unittest
from importlib.metadata import version
from pathlib import Path


class VendorSnapshotTests(unittest.TestCase):
    def test_arena_and_verifier_import(self) -> None:
        import agent_reliability_arena
        import completion_verifier

        self.assertEqual(agent_reliability_arena.__version__, "0.1.0")
        self.assertTrue(hasattr(completion_verifier, "evaluate_case"))

    def test_snapshot_manifest_matches_source(self) -> None:
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "vendor_snapshot.json").read_text(encoding="utf-8"))
        package = root / "src" / "completion_verifier"
        rows = []
        for path in sorted(package.rglob("*.py")):
            rows.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        self.assertEqual(manifest["files"], rows)
        self.assertEqual(manifest["source_commit"], "f65fb3450e3c1d7db17f0192667b854d126cd190")

    def test_installed_distribution_version(self) -> None:
        self.assertEqual(version("agent-reliability-arena"), "0.1.0")


if __name__ == "__main__":
    unittest.main()
