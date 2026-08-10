from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from agent_reliability_arena.transports import (
    ModelCallRequest,
    ModelCallResult,
    ModelUsage,
    RecordingTransport,
    verify_transport_ledger,
)
from agent_reliability_arena.transports.base import canonical_json_sha256


FIXED_TIME = datetime(2026, 8, 10, 8, 30, tzinfo=timezone.utc)


def make_request(call_id: str, input_text: str | None = None) -> ModelCallRequest:
    return ModelCallRequest(
        call_id=call_id,
        condition="general",
        role="general",
        model_id="fixture-model",
        model_version="2026-08-10",
        prompt_version="ledger-schema-v2",
        instructions="Return a concise response.",
        input_text=input_text or f"Record {call_id}.",
        max_output_tokens=128,
        seed=1304,
        metadata={"scenario": "schema-v2"},
    )


def make_result(request: ModelCallRequest, output_text: str | None = None) -> ModelCallResult:
    return ModelCallResult(
        call_id=request.call_id,
        request_digest=request.digest,
        provider="fixture-provider",
        response_id=f"response-{request.call_id}",
        model_id=request.model_id,
        output_text=output_text or f"recorded {request.call_id}",
        status="completed",
        latency_ms=12,
        usage=ModelUsage(input_tokens=8, output_tokens=3, total_tokens=11),
        raw_response_sha256="a" * 64,
        client_request_id=f"arena-{request.digest}",
        provider_request_id=f"provider-{request.call_id}",
        provider_processing_ms=7,
    )


class StaticTransport:
    provider = "fixture-provider"

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        return make_result(request)


def load_rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def legacy_v1_row(
    request: ModelCallRequest,
    *,
    sequence: int,
    recorded_at: str,
    result: ModelCallResult | None = None,
) -> dict[str, object]:
    if result is None:
        result = make_result(request)
    unsigned: dict[str, object] = {
        "schema_version": "1",
        "sequence": sequence,
        "recorded_at": recorded_at,
        "provider": "fixture-provider",
        "request": request.to_dict(),
        "request_digest": request.digest,
        "outcome_type": "result",
        "result": result.to_dict(),
        "error": None,
    }
    return {**unsigned, "record_digest": canonical_json_sha256(unsigned)}


class TransportLedgerSchemaV2Tests(unittest.TestCase):
    def test_new_ledger_defaults_to_schema2_and_links_second_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            recorder = RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME)

            recorder.complete(make_request("call-1"))
            recorder.complete(make_request("call-2"))

            rows = load_rows(ledger)
            self.assertEqual([row["schema_version"] for row in rows], ["2", "2"])
            self.assertIn("previous_record_digest", rows[0])
            self.assertIsNone(rows[0]["previous_record_digest"])
            self.assertEqual(rows[1]["previous_record_digest"], rows[0]["record_digest"])
            self.assertEqual(verify_transport_ledger(ledger)["schema_version"], "2")

    def test_existing_schema1_ledger_verifies_and_continues_without_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            first_request = make_request("legacy-1")
            first_row = legacy_v1_row(
                first_request,
                sequence=1,
                recorded_at="2026-08-10T08:30:00Z",
            )
            write_rows(ledger, [first_row])
            original_bytes = ledger.read_bytes()

            before = verify_transport_ledger(ledger)
            self.assertEqual(before["schema_version"], "1")
            self.assertEqual(before["records"], 1)

            recorder = RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME)
            recorder.complete(make_request("legacy-2"))

            rows = load_rows(ledger)
            self.assertTrue(ledger.read_bytes().startswith(original_bytes))
            self.assertEqual([row["schema_version"] for row in rows], ["1", "1"])
            self.assertNotIn("previous_record_digest", rows[1])
            after = verify_transport_ledger(ledger)
            self.assertEqual(after["schema_version"], "1")
            self.assertEqual(after["records"], 2)

    def test_rejects_modified_prior_record_even_if_its_digest_is_recomputed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            recorder = RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME)
            recorder.complete(make_request("call-1"))
            recorder.complete(make_request("call-2"))
            rows = load_rows(ledger)
            self.assertEqual(rows[1].get("previous_record_digest"), rows[0]["record_digest"])

            rows[0]["recorded_at"] = "2026-08-10T08:31:00Z"
            unsigned = dict(rows[0])
            unsigned.pop("record_digest")
            rows[0]["record_digest"] = canonical_json_sha256(unsigned)
            write_rows(ledger, rows)

            with self.assertRaisesRegex(ValueError, "previous.*digest|digest.*previous|chain"):
                verify_transport_ledger(ledger)

    def test_rejects_non_null_schema2_genesis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME).complete(
                make_request("call-1")
            )
            rows = load_rows(ledger)
            self.assertIn("previous_record_digest", rows[0])
            rows[0]["previous_record_digest"] = "f" * 64
            unsigned = dict(rows[0])
            unsigned.pop("record_digest")
            rows[0]["record_digest"] = canonical_json_sha256(unsigned)
            write_rows(ledger, rows)

            with self.assertRaisesRegex(ValueError, "previous.*digest|genesis"):
                verify_transport_ledger(ledger)

    def test_rejects_mixed_schema_versions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            recorder = RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME)
            recorder.complete(make_request("call-1"))
            recorder.complete(make_request("call-2"))
            rows = load_rows(ledger)
            self.assertEqual(rows[0].get("schema_version"), "2")

            second_request = make_request("legacy-replacement")
            rows[1] = legacy_v1_row(
                second_request,
                sequence=2,
                recorded_at="2026-08-10T08:31:00Z",
            )
            write_rows(ledger, rows)

            with self.assertRaisesRegex(ValueError, "schema"):
                verify_transport_ledger(ledger)

    def test_rejects_middle_record_deletion_from_schema2_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            recorder = RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME)
            for index in range(1, 4):
                recorder.complete(make_request(f"call-{index}"))
            rows = load_rows(ledger)
            self.assertEqual(rows[2].get("previous_record_digest"), rows[1]["record_digest"])

            write_rows(ledger, [rows[0], rows[2]])

            with self.assertRaises(ValueError):
                verify_transport_ledger(ledger)

    def test_rejects_reordered_schema2_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            recorder = RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME)
            for index in range(1, 4):
                recorder.complete(make_request(f"call-{index}"))
            rows = load_rows(ledger)
            self.assertEqual(rows[1].get("previous_record_digest"), rows[0]["record_digest"])

            write_rows(ledger, [rows[0], rows[2], rows[1]])

            with self.assertRaises(ValueError):
                verify_transport_ledger(ledger)

    def test_rejects_unsupported_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            request = make_request("unsupported")
            row = legacy_v1_row(
                request,
                sequence=1,
                recorded_at="2026-08-10T08:30:00Z",
            )
            row["schema_version"] = "99"
            unsigned = dict(row)
            unsigned.pop("record_digest")
            row["record_digest"] = canonical_json_sha256(unsigned)
            write_rows(ledger, [row])

            with self.assertRaisesRegex(ValueError, "schema"):
                verify_transport_ledger(ledger)


if __name__ == "__main__":
    unittest.main()
