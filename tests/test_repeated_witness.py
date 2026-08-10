from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.repeated_witness import (
    WITNESS_FILENAME,
    append_completed_trial_witness,
    verify_completed_trial_witnesses,
)
from agent_reliability_arena.transports import RecordingTransport
from agent_reliability_arena.transports.base import canonical_json_sha256
from test_transport_ledger import FIXED_TIME, StaticTransport, make_request, make_result


PLAN_DIGEST = "1" * 64
PREFLIGHT_DIGEST = "2" * 64


def make_trial(root: Path, trial_id: str, call_id: str) -> Path:
    trial_root = root / trial_id
    trial_root.mkdir(parents=True)
    request = make_request(call_id)
    RecordingTransport(
        StaticTransport(make_result(request, f"result-{trial_id}")),
        trial_root / "transport-calls.jsonl",
        clock=lambda: FIXED_TIME,
    ).complete(request)
    (trial_root / "verification-summary.json").write_text(
        json.dumps(
            {
                "schema_version": "fixture-trial-summary-v1",
                "status": "completed",
                "trial_id": trial_id,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return trial_root


def witness_rows(root: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (root / WITNESS_FILENAME).read_text(encoding="utf-8").splitlines()
    ]


class RepeatedWitnessTests(unittest.TestCase):
    def test_first_witness_commits_exact_verified_trial_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trial_root = make_trial(root, "trial-0001", "call-1")

            written = append_completed_trial_witness(
                root,
                "trial-0001",
                PLAN_DIGEST,
                PREFLIGHT_DIGEST,
            )
            rows = verify_completed_trial_witnesses(
                root,
                ["trial-0001"],
                PLAN_DIGEST,
                PREFLIGHT_DIGEST,
            )

            self.assertEqual(rows, [written])
            self.assertEqual(written["schema_version"], "arena-repeated-experiment-evidence-witness-v1")
            self.assertEqual(written["sequence"], 1)
            self.assertEqual(written["trial_id"], "trial-0001")
            self.assertEqual(written["plan_digest"], PLAN_DIGEST)
            self.assertEqual(written["preflight_manifest_digest"], PREFLIGHT_DIGEST)
            self.assertEqual(written["ledger_schema_version"], "2")
            self.assertEqual(written["ledger_records"], 1)
            self.assertEqual(
                written["ledger_sha256"],
                hashlib.sha256((trial_root / "transport-calls.jsonl").read_bytes()).hexdigest(),
            )
            self.assertEqual(
                written["verification_summary_sha256"],
                hashlib.sha256((trial_root / "verification-summary.json").read_bytes()).hexdigest(),
            )
            self.assertIsNone(written["previous_witness_digest"])
            unsigned = dict(written)
            digest = unsigned.pop("witness_digest")
            self.assertEqual(digest, canonical_json_sha256(unsigned))
            self.assertEqual(witness_rows(root), [written])

    def test_three_witnesses_form_monotonic_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(1, 4):
                trial_id = f"trial-{index:04d}"
                make_trial(root, trial_id, f"call-{index}")
                append_completed_trial_witness(root, trial_id, PLAN_DIGEST, PREFLIGHT_DIGEST)

            rows = verify_completed_trial_witnesses(
                root,
                ["trial-0001", "trial-0002", "trial-0003"],
                PLAN_DIGEST,
                PREFLIGHT_DIGEST,
            )
            self.assertEqual([row["sequence"] for row in rows], [1, 2, 3])
            self.assertIsNone(rows[0]["previous_witness_digest"])
            self.assertEqual(rows[1]["previous_witness_digest"], rows[0]["witness_digest"])
            self.assertEqual(rows[2]["previous_witness_digest"], rows[1]["witness_digest"])

    def test_rejects_mutated_witnessed_ledger_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trial_root = make_trial(root, "trial-0001", "call-1")
            append_completed_trial_witness(root, "trial-0001", PLAN_DIGEST, PREFLIGHT_DIGEST)

            ledger = trial_root / "transport-calls.jsonl"
            ledger.write_bytes(ledger.read_bytes() + b"\n")
            with self.assertRaises(ValueError):
                verify_completed_trial_witnesses(
                    root,
                    ["trial-0001"],
                    PLAN_DIGEST,
                    PREFLIGHT_DIGEST,
                )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trial_root = make_trial(root, "trial-0001", "call-1")
            append_completed_trial_witness(root, "trial-0001", PLAN_DIGEST, PREFLIGHT_DIGEST)

            summary = trial_root / "verification-summary.json"
            summary.write_bytes(summary.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "verification summary"):
                verify_completed_trial_witnesses(
                    root,
                    ["trial-0001"],
                    PLAN_DIGEST,
                    PREFLIGHT_DIGEST,
                )

    def test_requires_witness_length_to_equal_completed_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_trial(root, "trial-0001", "call-1")
            with self.assertRaisesRegex(ValueError, "missing"):
                verify_completed_trial_witnesses(
                    root,
                    ["trial-0001"],
                    PLAN_DIGEST,
                    PREFLIGHT_DIGEST,
                )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_trial(root, "trial-0001", "call-1")
            make_trial(root, "trial-0002", "call-2")
            append_completed_trial_witness(root, "trial-0001", PLAN_DIGEST, PREFLIGHT_DIGEST)
            with self.assertRaisesRegex(ValueError, "shorter"):
                verify_completed_trial_witnesses(
                    root,
                    ["trial-0001", "trial-0002"],
                    PLAN_DIGEST,
                    PREFLIGHT_DIGEST,
                )

            append_completed_trial_witness(root, "trial-0002", PLAN_DIGEST, PREFLIGHT_DIGEST)
            with self.assertRaisesRegex(ValueError, "ahead"):
                verify_completed_trial_witnesses(
                    root,
                    ["trial-0001"],
                    PLAN_DIGEST,
                    PREFLIGHT_DIGEST,
                )

    def test_rejects_witness_chain_shape_and_json_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_trial(root, "trial-0001", "call-1")
            make_trial(root, "trial-0002", "call-2")
            append_completed_trial_witness(root, "trial-0001", PLAN_DIGEST, PREFLIGHT_DIGEST)
            append_completed_trial_witness(root, "trial-0002", PLAN_DIGEST, PREFLIGHT_DIGEST)
            path = root / WITNESS_FILENAME
            rows = witness_rows(root)

            rows[1]["previous_witness_digest"] = "f" * 64
            unsigned = dict(rows[1])
            unsigned.pop("witness_digest")
            rows[1]["witness_digest"] = canonical_json_sha256(unsigned)
            path.write_text(
                "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "previous_witness_digest"):
                verify_completed_trial_witnesses(
                    root,
                    ["trial-0001", "trial-0002"],
                    PLAN_DIGEST,
                    PREFLIGHT_DIGEST,
                )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_trial(root, "trial-0001", "call-1")
            append_completed_trial_witness(root, "trial-0001", PLAN_DIGEST, PREFLIGHT_DIGEST)
            path = root / WITNESS_FILENAME
            row = witness_rows(root)[0]
            row["unexpected"] = True
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "shape"):
                verify_completed_trial_witnesses(
                    root,
                    ["trial-0001"],
                    PLAN_DIGEST,
                    PREFLIGHT_DIGEST,
                )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_trial(root, "trial-0001", "call-1")
            (root / WITNESS_FILENAME).write_text("{not-json}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON"):
                verify_completed_trial_witnesses(
                    root,
                    ["trial-0001"],
                    PLAN_DIGEST,
                    PREFLIGHT_DIGEST,
                )


if __name__ == "__main__":
    unittest.main()
