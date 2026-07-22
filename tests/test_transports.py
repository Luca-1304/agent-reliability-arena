from __future__ import annotations

import hashlib
import io
import json
import unittest
import urllib.error
from email.message import Message

from agent_reliability_arena.transports import (
    ModelCallRequest,
    OpenAIResponsesTransport,
    TransportError,
)


def request() -> ModelCallRequest:
    return ModelCallRequest(
        call_id="fixture--general--success--1",
        condition="general",
        role="general",
        model_id="gpt-test-snapshot",
        model_version="2026-07-22",
        prompt_version="live-prompts-v1",
        instructions="Return a concise plan.",
        input_text="Write the exact contracted file.",
        max_output_tokens=256,
        seed=1304,
        metadata={"scenario": "success"},
    )


class FakeResponse:
    def __init__(self, payload: dict, request_id: str = "req_test") -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.headers = Message()
        self.headers["x-request-id"] = request_id

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


class TransportTests(unittest.TestCase):
    def test_request_digest_is_deterministic_and_versioned(self) -> None:
        first = request()
        second = request()
        self.assertEqual(first.digest, second.digest)
        self.assertEqual(len(first.digest), 64)
        changed = ModelCallRequest(**(first.to_dict() | {"prompt_version": "live-prompts-v2"}))
        self.assertNotEqual(first.digest, changed.digest)
        spaced = ModelCallRequest(**(first.to_dict() | {"input_text": "  exact input\n"}))
        self.assertEqual(spaced.input_text, "  exact input\n")

    def test_openai_transport_parses_text_usage_and_request_id(self) -> None:
        seen = {}

        def opener(http_request, timeout):
            seen["timeout"] = timeout
            seen["authorization"] = http_request.headers["Authorization"]
            seen["payload"] = json.loads(http_request.data.decode("utf-8"))
            payload = {
                "id": "resp_test",
                "model": "gpt-test-snapshot",
                "status": "completed",
                "output": [
                    {"type": "message", "content": [{"type": "output_text", "text": "first"}]},
                    {"type": "message", "content": [{"type": "output_text", "text": " second"}]},
                ],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 4,
                    "total_tokens": 14,
                    "input_tokens_details": {"cached_tokens": 3},
                    "output_tokens_details": {"reasoning_tokens": 2},
                },
            }
            seen["raw"] = json.dumps(payload).encode("utf-8")
            return FakeResponse(payload)

        ticks = iter((1_000_000_000, 1_025_000_000))
        transport = OpenAIResponsesTransport(
            api_key="secret-test-key",
            opener=opener,
            clock_ns=lambda: next(ticks),
        )
        result = transport.complete(request())
        self.assertEqual(result.output_text, "first second")
        self.assertEqual(result.latency_ms, 25)
        self.assertEqual(result.provider_request_id, "req_test")
        self.assertEqual(result.raw_response_sha256, hashlib.sha256(seen["raw"]).hexdigest())
        self.assertEqual(result.usage.to_dict()["cached_input_tokens"], 3)
        self.assertEqual(result.usage.to_dict()["reasoning_tokens"], 2)
        self.assertFalse(seen["payload"]["store"])
        self.assertEqual(seen["payload"]["metadata"]["arena_prompt_version"], "live-prompts-v1")
        self.assertEqual(seen["authorization"], "Bearer secret-test-key")
        self.assertNotIn("secret-test-key", json.dumps(result.to_dict()))

    def test_http_errors_are_classified_without_leaking_key(self) -> None:
        headers = Message()
        headers["x-request-id"] = "req_rate_limit"
        error = urllib.error.HTTPError(
            url="https://api.openai.com/v1/responses",
            code=429,
            msg="Too Many Requests",
            hdrs=headers,
            fp=io.BytesIO(json.dumps({"error": {"message": "Rate limited."}}).encode("utf-8")),
        )
        transport = OpenAIResponsesTransport(
            api_key="secret-test-key",
            opener=lambda *args, **kwargs: (_ for _ in ()).throw(error),
        )
        with self.assertRaises(TransportError) as raised:
            transport.complete(request())
        self.assertTrue(raised.exception.retryable)
        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.provider_request_id, "req_rate_limit")
        self.assertNotIn("secret-test-key", str(raised.exception))

    def test_accepts_refusal_as_a_valid_model_result(self) -> None:
        transport = OpenAIResponsesTransport(
            api_key="x",
            opener=lambda *args, **kwargs: FakeResponse(
                {
                    "id": "resp-refusal",
                    "model": "gpt-test",
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "refusal", "refusal": "I cannot do that."}],
                        }
                    ],
                }
            ),
        )
        result = transport.complete(request())
        self.assertEqual(result.output_text, "")
        self.assertEqual(result.refusal_text, "I cannot do that.")

    def test_rejects_insecure_or_implicit_custom_endpoint_and_missing_content(self) -> None:
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            OpenAIResponsesTransport(api_key="x", endpoint="http://example.com/v1/responses")
        with self.assertRaisesRegex(ValueError, "Custom endpoints"):
            OpenAIResponsesTransport(api_key="x", endpoint="https://example.com/v1/responses")
        custom = OpenAIResponsesTransport(
            api_key="x",
            endpoint="https://example.com/v1/responses",
            allow_custom_endpoint=True,
            opener=lambda *args, **kwargs: FakeResponse(
                {
                    "id": "resp-custom",
                    "model": "gpt-test",
                    "output": [
                        {"type": "message", "content": [{"type": "output_text", "text": "ok"}]}
                    ],
                }
            ),
        )
        self.assertEqual(custom.complete(request()).output_text, "ok")
        transport = OpenAIResponsesTransport(
            api_key="x",
            opener=lambda *args, **kwargs: FakeResponse(
                {"id": "resp", "model": "gpt-test", "output": []}
            ),
        )
        with self.assertRaisesRegex(TransportError, "no output_text or refusal"):
            transport.complete(request())


if __name__ == "__main__":
    unittest.main()
