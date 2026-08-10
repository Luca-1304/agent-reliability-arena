from __future__ import annotations

import json
import unittest
from email.message import Message

from agent_reliability_arena.transports import (
    ModelCallRequest,
    OpenAIResponsesTransport,
    TransportError,
)


def request() -> ModelCallRequest:
    return ModelCallRequest(
        call_id="stage7--general--success--1",
        condition="general",
        role="general",
        model_id="gpt-5.5-2026-04-23",
        model_version="gpt-5.5-2026-04-23",
        prompt_version="fixture-prompts-v1",
        instructions="Return the exact contracted output.",
        input_text="Write the exact contracted file.",
        max_output_tokens=256,
        seed=1304,
        metadata={"scenario_id": "success", "attempt_number": "1"},
    )


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.headers = Message()
        self.headers["x-request-id"] = "req_stage7_model_identity"

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


class OpenAIModelProvenanceTests(unittest.TestCase):
    def test_missing_or_invalid_provider_model_identity_fails_closed(self) -> None:
        invalid_values = ("missing", None, "", "   ", 123)
        for value in invalid_values:
            with self.subTest(value=value):
                payload: dict[str, object] = {
                    "id": "resp_stage7",
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "ok"}],
                        }
                    ],
                    "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                }
                if value != "missing":
                    payload["model"] = value
                transport = OpenAIResponsesTransport(
                    api_key="test-only-key",
                    opener=lambda *args, payload=payload, **kwargs: FakeResponse(payload),
                )
                with self.assertRaises(TransportError) as raised:
                    transport.complete(request())
                self.assertEqual(raised.exception.category, "invalid_response")
                self.assertFalse(raised.exception.retryable)
                self.assertIn("model", str(raised.exception).lower())


if __name__ == "__main__":
    unittest.main()
