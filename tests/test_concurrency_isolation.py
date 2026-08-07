from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.ci.verify_concurrency import (
    ConcurrencyIsolationError,
    assert_disjoint_artifact_trees,
    build_run_environment,
)


class ConcurrencyIsolationTests(unittest.TestCase):
    def test_each_run_gets_disjoint_home_temp_cache_and_seed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = build_run_environment(base={"PATH": "/usr/bin"}, root=root / "run-a", hash_seed=3)
            second = build_run_environment(base={"PATH": "/usr/bin"}, root=root / "run-b", hash_seed=11)
            for key in ("HOME", "TMPDIR", "TEMP", "TMP", "PIP_CACHE_DIR", "XDG_CACHE_HOME"):
                self.assertNotEqual(first[key], second[key])
            self.assertEqual(first["PYTHONHASHSEED"], "3")
            self.assertEqual(second["PYTHONHASHSEED"], "11")

    def test_disjoint_trees_pass_when_no_cross_run_files_exist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = root / "left"
            right = root / "right"
            (left / "artifacts").mkdir(parents=True)
            (right / "artifacts").mkdir(parents=True)
            (left / "artifacts" / "result.json").write_text("left", encoding="utf-8")
            (right / "artifacts" / "result.json").write_text("right", encoding="utf-8")
            assert_disjoint_artifact_trees(left, right)

    def test_hardlinks_within_one_run_do_not_look_like_cross_run_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = root / "left"
            right = root / "right"
            left.mkdir()
            right.mkdir()
            original = left / "original.txt"
            original.write_text("same-run", encoding="utf-8")
            try:
                (left / "alias.txt").hardlink_to(original)
            except (OSError, NotImplementedError):
                self.skipTest("hard links unavailable on this platform")
            assert_disjoint_artifact_trees(left, right)

    def test_symlink_crossing_into_other_run_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = root / "left"
            right = root / "right"
            left.mkdir()
            right.mkdir()
            target = right / "result.json"
            target.write_text("right", encoding="utf-8")
            try:
                (left / "cross-run").symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable on this platform")
            with self.assertRaisesRegex(ConcurrencyIsolationError, "cross-run symlink"):
                assert_disjoint_artifact_trees(left, right)

    def test_shared_resolved_file_identity_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = root / "left"
            right = root / "right"
            left.mkdir()
            right.mkdir()
            shared = root / "shared.txt"
            shared.write_text("shared", encoding="utf-8")
            try:
                (left / "shared.txt").hardlink_to(shared)
                (right / "shared.txt").hardlink_to(shared)
            except (OSError, NotImplementedError):
                self.skipTest("hard links unavailable on this platform")
            with self.assertRaisesRegex(ConcurrencyIsolationError, "shared file identity"):
                assert_disjoint_artifact_trees(left, right)


if __name__ == "__main__":
    unittest.main()
