from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.verify_determinism import (
    DeterminismError,
    canonical_json_bytes,
    compare_json_values,
    compare_outputs,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "reliability-policy.json"


class DeterminismTests(unittest.TestCase):
    def test_policy_declares_explicit_deterministic_output_classes(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        outputs = payload["deterministic_outputs"]
        self.assertEqual(outputs["fixture_run"]["class"], "semantic")
        self.assertEqual(outputs["fixture_replay"]["class"], "semantic")
        self.assertEqual(outputs["public_export"]["class"], "semantic")
        self.assertEqual(outputs["wheel_contents"]["class"], "semantic")
        for rule in outputs.values():
            self.assertIn(rule["class"], {"byte", "semantic", "bounded"})

    def test_semantic_json_ignores_formatting_and_key_order_not_values(self) -> None:
        left = b'{"b":2,"a":1}\n'
        right = b'{\n  "a": 1,\n  "b": 2\n}\n'
        changed = b'{"a":1,"b":3}'
        self.assertEqual(canonical_json_bytes(left), canonical_json_bytes(right))
        self.assertNotEqual(canonical_json_bytes(left), canonical_json_bytes(changed))

    def test_json_comparison_reports_pointer_for_unlisted_difference(self) -> None:
        result = compare_json_values({"a": {"b": 1}}, {"a": {"b": 2}}, ignored_pointers=())
        self.assertFalse(result.equal)
        self.assertIn("/a/b", result.diff)

    def test_explicit_pointer_can_ignore_known_volatile_field(self) -> None:
        result = compare_json_values(
            {"stable": 1, "meta": {"path": "/tmp/a"}},
            {"stable": 1, "meta": {"path": "/tmp/b"}},
            ignored_pointers=("/meta/path",),
        )
        self.assertTrue(result.equal)
        self.assertEqual(result.diff, "")

    def test_ignore_pointer_missing_on_either_side_fails_closed(self) -> None:
        with self.assertRaisesRegex(DeterminismError, "ignored pointer"):
            compare_json_values(
                {"stable": 1},
                {"stable": 1, "meta": {"path": "/tmp/b"}},
                ignored_pointers=("/meta/path",),
            )

    def test_byte_class_requires_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = root / "left.bin"
            right = root / "right.bin"
            left.write_bytes(b"abc\n")
            right.write_bytes(b"abc")
            result = compare_outputs(left, right, {"class": "byte", "format": "binary"})
            self.assertFalse(result.equal)

    def test_semantic_json_comparison_writes_normalized_diff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = root / "left.json"
            right = root / "right.json"
            left.write_text('{"value": 1, "other": true}\n', encoding="utf-8")
            right.write_text('{"value": 2, "other": true}\n', encoding="utf-8")
            result = compare_outputs(
                left,
                right,
                {"class": "semantic", "format": "json", "ignore_json_pointers": []},
            )
            self.assertFalse(result.equal)
            self.assertIn('"value": 1', result.diff)
            self.assertIn('"value": 2', result.diff)

    def test_bounded_class_requires_explicit_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = root / "left.json"
            right = root / "right.json"
            left.write_text('{"status": "ok"}', encoding="utf-8")
            right.write_text('{"status": "ok"}', encoding="utf-8")
            with self.assertRaisesRegex(DeterminismError, "invariants"):
                compare_outputs(left, right, {"class": "bounded", "format": "json"})


if __name__ == "__main__":
    unittest.main()
