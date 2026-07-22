from __future__ import annotations

import hashlib
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
    TransportError,
    verify_transport_ledger,
)
from agent_reliability_arena.transports.base import canonical_json_sha256


FIXED_TIME = datetime(2026, 7, 22, 18, 0, tzinfo=timezone.utc)


def make_request(call_id: str = "call-1", input_text: str = "Write the contracted output.") -> ModelCallRequest:
    return ModelCallRequest(
        call_id=call_id,
        condition="general",
        role="general",
        model_id="fixture-model",
        model_version="2026-07-22",
        prompt_version="ledger-prompts-v1",
        instructions="Return a concise response.",
        input_text=input_text,
        max_output_tokens=128,
        seed=1304,
        metadata={"scenario": "success"},
    )


def make_result(request: ModelCallRequest, output_text: str = "recorded") -> ModelCallResult:
    return ModelCallResult(
        call_id=request.call_id,
        request_digest=request.digest,
        provider="fixture-provider",
        response_id=f"response-{request.call_id}",
        model_id=request.model_id,
        output_text=output_text,
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

    def __init__(self, result: ModelCallResult) -> None:
        self.result = result
        self.calls = 0

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        self.calls += 1
        return self.result


class ErrorTransport:
    provider = "fixture-provider"

    def __init__(self, error: TransportError) -> None:
        self.error = error
        self.calls = 0

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        self.calls += 1
        raise self.error


class TransportLedgerTests(unittest.TestCase):
    def test_records_success_and_returns_original_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            model_request = make_request()
            expected = make_result(model_request)
            wrapped = StaticTransport(expected)
            recorder = RecordingTransport(wrapped, ledger, clock=lambda: FIXED_TIME)

            actual = recorder.complete(model_request)

            self.assertIs(actual, expected)
            self.assertEqual(wrapped.calls, 1)
            self.assertTrue(ledger.is_file())
            lines = ledger.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            row = json.loads(lines[0])
            self.assertEqual(row["schema_version"], "1")
            self.assertEqual(row["sequence"], 1)
            self.assertEqual(row["recorded_at"], "2026-07-22T18:00:00Z")
            self.assertEqual(row["provider"], "fixture-provider")
            self.assertEqual(row["outcome_type"], "result")
            self.assertEqual(row["request"], model_request.to_dict())
            self.assertEqual(row["request_digest"], model_request.digest)
            self.assertEqual(row["result"], expected.to_dict())
            self.assertIsNone(row["error"])
            digest = row.pop("record_digest")
            self.assertEqual(digest, canonical_json_sha256(row))

    def test_records_transport_error_and_reraises_same_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            model_request = make_request()
            error = TransportError(
                "rate limited",
                category="http_error",
                retryable=True,
                status_code=429,
                client_request_id=f"arena-{model_request.digest}",
                provider_request_id="req-rate-limit",
            )
            wrapped = ErrorTransport(error)
            recorder = RecordingTransport(wrapped, ledger, clock=lambda: FIXED_TIME)

            with self.assertRaises(TransportError) as raised:
                recorder.complete(model_request)

            self.assertIs(raised.exception, error)
            self.assertEqual(wrapped.calls, 1)
            row = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(row["outcome_type"], "error")
            self.assertIsNone(row["result"])
            self.assertEqual(row["error"], error.to_dict())
            verify = verify_transport_ledger(ledger)
            self.assertEqual(verify["records"], 1)
            self.assertEqual(verify["results"], 0)
            self.assertEqual(verify["errors"], 1)

    def test_verifies_ledger_and_continues_sequence_after_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            first_request = make_request("call-1")
            first = RecordingTransport(
                StaticTransport(make_result(first_request, "first")),
                ledger,
                clock=lambda: FIXED_TIME,
            )
            first.complete(first_request)

            summary = verify_transport_ledger(ledger)
            self.assertEqual(summary["records"], 1)
            self.assertEqual(summary["results"], 1)
            self.assertEqual(summary["errors"], 0)
            self.assertEqual(summary["ledger_sha256"], hashlib.sha256(ledger.read_bytes()).hexdigest())

            second_request = make_request("call-2", "Second input.")
            second = RecordingTransport(
                StaticTransport(make_result(second_request, "second")),
                ledger,
                clock=lambda: datetime(2026, 7, 22, 18, 1, tzinfo=timezone.utc),
            )
            second.complete(second_request)

            rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["sequence"] for row in rows], [1, 2])
            self.assertEqual(verify_transport_ledger(ledger)["records"], 2)

    def test_rejects_tampered_record_even_when_line_digest_is_recomputed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            model_request = make_request()
            RecordingTransport(
                StaticTransport(make_result(model_request)),
                ledger,
                clock=lambda: FIXED_TIME,
            ).complete(model_request)
            row = json.loads(ledger.read_text(encoding="utf-8"))
            row["result"]["call_id"] = "different-call"
            row_without_digest = dict(row)
            row_without_digest.pop("record_digest")
            row["record_digest"] = canonical_json_sha256(row_without_digest)
            ledger.write_text(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "call_id"):
                verify_transport_ledger(ledger)

    def test_rejects_missing_parent_and_symlink_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model_request = make_request()
            transport = StaticTransport(make_result(model_request))
            with self.assertRaisesRegex(ValueError, "parent"):
                RecordingTransport(transport, root / "missing" / "calls.jsonl")

            target = root / "target.jsonl"
            target.write_text("", encoding="utf-8")
            link = root / "link.jsonl"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"Symlink creation unavailable: {exc}")
            with self.assertRaisesRegex(ValueError, "symlink"):
                RecordingTransport(transport, link)
            with self.assertRaisesRegex(ValueError, "symlink"):
                verify_transport_ledger(link)

    def test_verification_never_executes_provider(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            model_request = make_request()
            transport = StaticTransport(make_result(model_request))
            RecordingTransport(transport, ledger, clock=lambda: FIXED_TIME).complete(model_request)
            self.assertEqual(transport.calls, 1)

            verify_transport_ledger(ledger)

            self.assertEqual(transport.calls, 1)


if __name__ == "__main__":
    unittest.main()
