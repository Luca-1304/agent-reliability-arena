from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.reliability_evidence import (
    EvidenceManifest,
    FailureRecord,
    append_jsonl,
    dependency_fingerprint,
    sha256_bytes,
    write_json_atomic,
)


class ReliabilityEvidenceTests(unittest.TestCase):
    def test_failure_record_uses_controlled_vocabulary(self) -> None:
        record = FailureRecord(
            category="TIMEOUT",
            phase="deep",
            command_name="unit-tests",
            argv=("python", "-m", "unittest"),
            sequence=4,
            pass_number=2,
            hash_seed=1,
            exit_code=124,
            duration_seconds=900.0,
            log_path="passes/02/commands/04-unit-tests.log",
            message="command timed out",
        )
        payload = record.to_dict()
        self.assertEqual(payload["category"], "TIMEOUT")
        self.assertEqual(payload["sequence"], 4)
        self.assertEqual(payload["argv"], ["python", "-m", "unittest"])

    def test_unknown_failure_category_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported failure category"):
            FailureRecord(
                category="wheel-cli",
                phase="wheel",
                command_name="run",
                argv=("arena-run",),
                sequence=1,
                pass_number=1,
                hash_seed=0,
                exit_code=1,
                duration_seconds=0.1,
                log_path="run.log",
                message="failed",
            )

    def test_manifest_is_machine_readable_versioned_and_sorted(self) -> None:
        manifest = EvidenceManifest.minimum_for_test(commit_sha="a" * 40)
        manifest.commands.extend(
            [
                {"sequence": 3, "name": "third"},
                {"sequence": 1, "name": "first"},
            ]
        )
        manifest.failures.extend(
            [
                FailureRecord(
                    category="TEST",
                    phase="deep",
                    command_name="later",
                    argv=("python",),
                    sequence=9,
                    pass_number=2,
                    hash_seed=1,
                    exit_code=1,
                    duration_seconds=0.2,
                    log_path="later.log",
                    message="later",
                ),
                FailureRecord(
                    category="BUILD",
                    phase="deep",
                    command_name="earlier",
                    argv=("python",),
                    sequence=2,
                    pass_number=1,
                    hash_seed=0,
                    exit_code=1,
                    duration_seconds=0.1,
                    log_path="earlier.log",
                    message="earlier",
                ),
            ]
        )
        payload = manifest.to_dict()
        self.assertEqual(payload["schema_version"], "reliability-evidence-v1")
        self.assertEqual(payload["commit_sha"], "a" * 40)
        self.assertEqual([row["sequence"] for row in payload["commands"]], [1, 3])
        self.assertEqual([row["sequence"] for row in payload["failures"]], [2, 9])
        self.assertIn("toolchain", payload)
        self.assertIn("dependency_fingerprint", payload)
        self.assertIn("output_digests", payload)
        self.assertIn("timings", payload)

    def test_invalid_commit_sha_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "40-character"):
            EvidenceManifest.minimum_for_test(commit_sha="not-a-sha")

    def test_atomic_json_never_leaves_partial_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "nested" / "manifest.json"
            write_json_atomic(target, {"z": 1, "a": 2})
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                '{\n  "a": 2,\n  "z": 1\n}\n',
            )
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"a": 2, "z": 1})
            leftovers = [path for path in target.parent.iterdir() if path.name != target.name]
            self.assertEqual(leftovers, [])

    def test_jsonl_appends_one_canonical_record_per_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "events.jsonl"
            append_jsonl(target, {"z": 2, "a": 1})
            append_jsonl(target, {"event": "done"})
            lines = target.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], '{"a":1,"z":2}')
            self.assertEqual(json.loads(lines[1]), {"event": "done"})

    def test_dependency_fingerprint_is_order_independent_and_duplicate_free(self) -> None:
        first = dependency_fingerprint(["wheel==1", "pip==2", "wheel==1"])
        second = dependency_fingerprint(["pip==2", "wheel==1"])
        self.assertEqual(first, second)
        self.assertEqual(first["rows"], ["pip==2", "wheel==1"])
        self.assertEqual(first["sha256"], sha256_bytes(b"pip==2\nwheel==1\n"))


if __name__ == "__main__":
    unittest.main()
