from __future__ import annotations

import unittest
from unittest.mock import patch

from agent_reliability_arena.transports import ModelCallRequest, OpenAIResponsesTransport, TransportError


def request() -> ModelCallRequest:
    return ModelCallRequest(
        call_id="release--general--success--1",
        condition="general",
        role="general",
        model_id="gpt-test-snapshot",
        model_version="2026-07-22",
        prompt_version="live-prompts-v1",
        instructions="Return structured JSON only.",
        input_text='{"task":"controlled"}',
        max_output_tokens=64,
        seed=1304,
        metadata={"scenario_id": "success"},
    )


class ExternalExecutionBoundaryTests(unittest.TestCase):
    def test_real_opener_is_blocked_without_explicit_network_approval(self) -> None:
        with patch("urllib.request.urlopen", side_effect=AssertionError("network must not be touched")):
            transport = OpenAIResponsesTransport(api_key="present-but-not-authorised")
            with self.assertRaises(TransportError) as raised:
                transport.complete(request())
        self.assertEqual(raised.exception.category, "execution_disabled")
        self.assertFalse(raised.exception.retryable)
        self.assertNotIn("present-but-not-authorised", str(raised.exception))

    def test_injected_test_opener_remains_provider_free_without_network_approval(self) -> None:
        called = {"value": False}

        class Response:
            headers = {}

            def read(self) -> bytes:
                return b'{"id":"resp","model":"gpt-test","status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":"ok"}]}]}'

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback) -> None:
                return None

        def opener(*args, **kwargs):
            called["value"] = True
            return Response()

        transport = OpenAIResponsesTransport(api_key="test-key", opener=opener)
        self.assertEqual(transport.complete(request()).output_text, "ok")
        self.assertTrue(called["value"])


if __name__ == "__main__":
    unittest.main()
