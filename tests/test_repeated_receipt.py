from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.repeated_receipt import (
    RECEIPT_SCHEMA,
    main as receipt_main,
    verify_detached_witness_receipt,
    write_detached_witness_receipt,
)
from agent_reliability_arena.repeated_witness import (
    WITNESS_FILENAME,
    append_completed_trial_witness,
)
from agent_reliability_arena.transports.base import canonical_json_sha256
from test_repeated_witness import PLAN_DIGEST, PREFLIGHT_DIGEST, make_trial, witness_rows


RECEIPT_KEYS = {
    "schema_version",
    "plan_digest",
    "preflight_manifest_digest",
    "witness_records",
    "witness_prefix_bytes",
    "witness_prefix_sha256",
    "witness_head_digest",
    "last_trial_id",
    "receipt_digest",
}


def make_experiment(base: Path, trials: int = 1, *, call_prefix: str = "call") -> Path:
    root = base / "experiment"
    root.mkdir()
    (root / "experiment-plan.json").write_text(
        json.dumps(
            {
                "schema_version": "fixture-repeated-plan-record-v1",
                "plan_digest": PLAN_DIGEST,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "experiment-preflight.json").write_text(
        json.dumps(
            {
                "schema_version": "fixture-repeated-preflight-v1",
                "manifest_digest": PREFLIGHT_DIGEST,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    for index in range(1, trials + 1):
        trial_id = f"trial-{index:04d}"
        make_trial(root, trial_id, f"{call_prefix}-{index}")
        append_completed_trial_witness(root, trial_id, PLAN_DIGEST, PREFLIGHT_DIGEST)
    return root


def make_receipt_parent(base: Path) -> Path:
    parent = base / "receipts"
    parent.mkdir()
    return parent


class DetachedRepeatedWitnessReceiptTests(unittest.TestCase):
    def test_create_receipt_commits_exact_current_witness_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = make_receipt_parent(base) / "checkpoint-1.json"

            receipt = write_detached_witness_receipt(root, receipt_path)
            witness = (root / WITNESS_FILENAME).read_bytes()
            rows = witness_rows(root)

            self.assertEqual(set(receipt), RECEIPT_KEYS)
            self.assertEqual(receipt["schema_version"], RECEIPT_SCHEMA)
            self.assertEqual(receipt["plan_digest"], PLAN_DIGEST)
            self.assertEqual(receipt["preflight_manifest_digest"], PREFLIGHT_DIGEST)
            self.assertEqual(receipt["witness_records"], 1)
            self.assertEqual(receipt["witness_prefix_bytes"], len(witness))
            self.assertEqual(receipt["witness_prefix_sha256"], hashlib.sha256(witness).hexdigest())
            self.assertEqual(receipt["witness_head_digest"], rows[-1]["witness_digest"])
            self.assertEqual(receipt["last_trial_id"], "trial-0001")
            unsigned = dict(receipt)
            digest = unsigned.pop("receipt_digest")
            self.assertEqual(digest, canonical_json_sha256(unsigned))
            self.assertEqual(json.loads(receipt_path.read_text(encoding="utf-8")), receipt)

    def test_receipt_verifies_now_and_after_later_witness_appends(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = make_receipt_parent(base) / "checkpoint-1.json"
            receipt = write_detached_witness_receipt(root, receipt_path)

            immediate = verify_detached_witness_receipt(root, receipt_path)
            self.assertEqual(immediate["status"], "verified")
            self.assertEqual(immediate["receipt_witness_records"], 1)
            self.assertEqual(immediate["current_witness_records"], 1)
            self.assertFalse(immediate["later_records_present"])
            self.assertEqual(immediate["receipt_digest"], receipt["receipt_digest"])

            for index in (2, 3):
                trial_id = f"trial-{index:04d}"
                make_trial(root, trial_id, f"call-{index}")
                append_completed_trial_witness(root, trial_id, PLAN_DIGEST, PREFLIGHT_DIGEST)

            later = verify_detached_witness_receipt(root, receipt_path)
            self.assertEqual(later["status"], "verified")
            self.assertEqual(later["receipt_witness_records"], 1)
            self.assertEqual(later["current_witness_records"], 3)
            self.assertTrue(later["later_records_present"])

    def test_create_rejects_inside_root_existing_and_symlink_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            with self.assertRaisesRegex(ValueError, "outside"):
                write_detached_witness_receipt(root, root / "receipt.json")

            receipt_parent = make_receipt_parent(base)
            existing = receipt_parent / "existing.json"
            existing.write_text("already here\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "new|exist"):
                write_detached_witness_receipt(root, existing)

            link = receipt_parent / "link.json"
            target = receipt_parent / "target.json"
            target.write_text("target\n", encoding="utf-8")
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"Symlink creation unavailable: {exc}")
            with self.assertRaisesRegex(ValueError, "symlink"):
                write_detached_witness_receipt(root, link)

    def test_create_rejects_parent_symlink_resolving_inside_experiment_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            alias = base / "root-alias"
            try:
                alias.symlink_to(root, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"Directory symlink creation unavailable: {exc}")
            with self.assertRaisesRegex(ValueError, "outside"):
                write_detached_witness_receipt(root, alias / "receipt.json")

    def test_verify_rejects_changed_committed_witness_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = make_receipt_parent(base) / "checkpoint.json"
            write_detached_witness_receipt(root, receipt_path)

            witness = root / WITNESS_FILENAME
            raw = bytearray(witness.read_bytes())
            position = raw.index(b"trial-0001")
            raw[position + len("trial-")] = ord("9")
            witness.write_bytes(bytes(raw))

            with self.assertRaises(ValueError):
                verify_detached_witness_receipt(root, receipt_path)

    def test_retained_receipt_rejects_wholesale_locally_valid_history_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1, call_prefix="original")
            receipt_path = make_receipt_parent(base) / "checkpoint.json"
            old_receipt = write_detached_witness_receipt(root, receipt_path)

            shutil.rmtree(root / "trial-0001")
            (root / WITNESS_FILENAME).unlink()
            make_trial(root, "trial-0001", "replacement-call")
            append_completed_trial_witness(root, "trial-0001", PLAN_DIGEST, PREFLIGHT_DIGEST)
            replacement_rows = witness_rows(root)
            self.assertNotEqual(replacement_rows[-1]["witness_digest"], old_receipt["witness_head_digest"])

            with self.assertRaisesRegex(ValueError, "prefix|head"):
                verify_detached_witness_receipt(root, receipt_path)

    def test_verify_rejects_receipt_shape_digest_and_context_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = make_receipt_parent(base) / "checkpoint.json"
            receipt = write_detached_witness_receipt(root, receipt_path)

            unknown = dict(receipt)
            unknown["unexpected"] = True
            receipt_path.write_text(json.dumps(unknown) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "shape"):
                verify_detached_witness_receipt(root, receipt_path)

            receipt_path.write_text(
                '{"schema_version":"x","schema_version":"y"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                verify_detached_witness_receipt(root, receipt_path)

            receipt_path.write_text("{not-json}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON"):
                verify_detached_witness_receipt(root, receipt_path)

            tampered = dict(receipt)
            tampered["last_trial_id"] = "trial-9999"
            receipt_path.write_text(json.dumps(tampered) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "receipt_digest"):
                verify_detached_witness_receipt(root, receipt_path)

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = make_receipt_parent(base) / "checkpoint.json"
            write_detached_witness_receipt(root, receipt_path)
            plan_path = root / "experiment-plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["plan_digest"] = "9" * 64
            plan_path.write_text(json.dumps(plan) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "plan"):
                verify_detached_witness_receipt(root, receipt_path)

    def test_verify_rejects_current_witness_shorter_than_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 2)
            receipt_path = make_receipt_parent(base) / "checkpoint-2.json"
            write_detached_witness_receipt(root, receipt_path)

            witness = root / WITNESS_FILENAME
            first_line = witness.read_bytes().splitlines(keepends=True)[0]
            witness.write_bytes(first_line)

            with self.assertRaisesRegex(ValueError, "shorter"):
                verify_detached_witness_receipt(root, receipt_path)

    def test_module_cli_create_and_verify_print_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = make_receipt_parent(base) / "cli.json"

            create_output = io.StringIO()
            with contextlib.redirect_stdout(create_output):
                receipt_main(
                    [
                        "create",
                        "--experiment-root",
                        str(root),
                        "--receipt",
                        str(receipt_path),
                    ]
                )
            created = json.loads(create_output.getvalue())
            self.assertEqual(created["schema_version"], RECEIPT_SCHEMA)

            verify_output = io.StringIO()
            with contextlib.redirect_stdout(verify_output):
                receipt_main(
                    [
                        "verify",
                        "--experiment-root",
                        str(root),
                        "--receipt",
                        str(receipt_path),
                    ]
                )
            verified = json.loads(verify_output.getvalue())
            self.assertEqual(verified["status"], "verified")
            self.assertFalse(verified["later_records_present"])


if __name__ == "__main__":
    unittest.main()
