from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from .base import ModelCallRequest, ModelCallResult, ModelUsage, TransportError

_DEFAULT_ENDPOINT = "https://api.openai.com/v1/responses"
_RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}
_RETRYABLE_PROVIDER_ERROR_CODES = {
    "internal_error",
    "rate_limit_exceeded",
    "request_timeout",
    "server_error",
}


def _extract_content(payload: dict[str, Any], *, allow_empty: bool = False) -> tuple[str, str | None]:
    text_chunks: list[str] = []
    refusal_chunks: list[str] = []
    output = payload.get("output", [])
    if not isinstance(output, list):
        raise TransportError(
            "Provider response 'output' was not a list.",
            category="invalid_response",
            retryable=False,
        )
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "output_text":
                text = block.get("text")
                if isinstance(text, str) and text:
                    text_chunks.append(text)
            elif block.get("type") == "refusal":
                refusal = block.get("refusal")
                if isinstance(refusal, str) and refusal:
                    refusal_chunks.append(refusal)
    if not text_chunks and not refusal_chunks and not allow_empty:
        raise TransportError(
            "Provider response contained no output_text or refusal content.",
            category="invalid_response",
            retryable=False,
        )
    return "".join(text_chunks), "".join(refusal_chunks) or None


def _int_or_zero(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _optional_header_int(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _extract_usage(payload: dict[str, Any]) -> ModelUsage:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return ModelUsage(input_tokens=0, output_tokens=0, total_tokens=0)
    input_details = usage.get("input_tokens_details")
    output_details = usage.get("output_tokens_details")
    cached = _int_or_zero(input_details.get("cached_tokens")) if isinstance(input_details, dict) else 0
    reasoning = _int_or_zero(output_details.get("reasoning_tokens")) if isinstance(output_details, dict) else 0
    input_tokens = _int_or_zero(usage.get("input_tokens"))
    output_tokens = _int_or_zero(usage.get("output_tokens"))
    total_tokens = max(_int_or_zero(usage.get("total_tokens")), input_tokens + output_tokens)
    return ModelUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cached_input_tokens=cached,
        reasoning_tokens=reasoning,
    )


def _error_message(body: bytes, fallback: str) -> str:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return fallback
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
    return fallback


def _incomplete_reason(payload: dict[str, Any]) -> str | None:
    details = payload.get("incomplete_details")
    if not isinstance(details, dict):
        return None
    reason = details.get("reason")
    return reason if isinstance(reason, str) and reason.strip() else None


def _raise_failed_response(
    payload: dict[str, Any],
    *,
    client_request_id: str,
    provider_request_id: str | None,
) -> None:
    error = payload.get("error")
    code: str | None = None
    message = "The provider returned a failed response."
    if isinstance(error, dict):
        raw_code = error.get("code")
        raw_message = error.get("message")
        if isinstance(raw_code, str) and raw_code.strip():
            code = raw_code.strip()
        if isinstance(raw_message, str) and raw_message.strip():
            message = raw_message
    raise TransportError(
        message,
        category="provider_response_failed",
        retryable=code in _RETRYABLE_PROVIDER_ERROR_CODES,
        provider_error_code=code,
        client_request_id=client_request_id,
        provider_request_id=provider_request_id,
    )


class OpenAIResponsesTransport:
    provider = "openai-responses"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        endpoint: str = _DEFAULT_ENDPOINT,
        timeout_seconds: float = 120.0,
        allow_custom_endpoint: bool = False,
        opener: Callable[..., Any] | None = None,
        clock_ns: Callable[[], int] = time.perf_counter_ns,
    ) -> None:
        resolved_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
        if not isinstance(resolved_key, str) or not resolved_key.strip():
            raise ValueError("OPENAI_API_KEY is required for the OpenAI Responses transport.")
        parsed_endpoint = urlparse(endpoint) if isinstance(endpoint, str) else None
        if parsed_endpoint is None or parsed_endpoint.scheme != "https" or not parsed_endpoint.hostname:
            raise ValueError("'endpoint' must be an HTTPS URL.")
        if not isinstance(allow_custom_endpoint, bool):
            raise ValueError("'allow_custom_endpoint' must be a boolean.")
        if parsed_endpoint.hostname != "api.openai.com" and not allow_custom_endpoint:
            raise ValueError("Custom endpoints require allow_custom_endpoint=True.")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
            raise ValueError("'timeout_seconds' must be greater than zero.")
        self._api_key = resolved_key.strip()
        self.endpoint = endpoint
        self.timeout_seconds = float(timeout_seconds)
        self._opener = opener or urllib.request.urlopen
        self._clock_ns = clock_ns

    def _provider_payload(self, request: ModelCallRequest) -> dict[str, Any]:
        return {
            "model": request.model_id,
            "instructions": request.instructions,
            "input": request.input_text,
            "max_output_tokens": request.max_output_tokens,
            "store": False,
            "metadata": {
                "arena_call_id": request.call_id,
                "arena_condition": request.condition,
                "arena_role": request.role,
                "arena_prompt_version": request.prompt_version,
            },
        }

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        if not isinstance(request, ModelCallRequest):
            raise ValueError("'request' must be a ModelCallRequest instance.")
        payload = self._provider_payload(request)
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        client_request_id = f"arena-{request.digest}"
        http_request = urllib.request.Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "User-Agent": "agent-reliability-arena/0.2",
                "X-Client-Request-Id": client_request_id,
            },
        )
        started = self._clock_ns()
        try:
            with self._opener(http_request, timeout=self.timeout_seconds) as response:
                raw = response.read()
                provider_request_id = response.headers.get("x-request-id")
                provider_processing_ms = _optional_header_int(response.headers.get("openai-processing-ms"))
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            request_id = exc.headers.get("x-request-id") if exc.headers is not None else None
            raise TransportError(
                _error_message(raw, f"OpenAI API returned HTTP {exc.code}."),
                category="http_error",
                retryable=exc.code in _RETRYABLE_STATUS_CODES,
                status_code=exc.code,
                client_request_id=client_request_id,
                provider_request_id=request_id,
            ) from None
        except urllib.error.URLError as exc:
            raise TransportError(
                f"OpenAI API connection failed: {exc.reason}",
                category="network_error",
                retryable=True,
                client_request_id=client_request_id,
            ) from None
        elapsed_ms = max(0, (self._clock_ns() - started) // 1_000_000)
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TransportError(
                "OpenAI API returned invalid JSON.",
                category="invalid_response",
                retryable=False,
                client_request_id=client_request_id,
                provider_request_id=provider_request_id,
            ) from exc
        if not isinstance(decoded, dict):
            raise TransportError(
                "OpenAI API returned a non-object response.",
                category="invalid_response",
                retryable=False,
                client_request_id=client_request_id,
                provider_request_id=provider_request_id,
            )
        response_id = decoded.get("id")
        response_model = decoded.get("model")
        status = decoded.get("status", "completed")
        if not isinstance(response_id, str) or not response_id:
            raise TransportError(
                "OpenAI API response did not include an id.",
                category="invalid_response",
                retryable=False,
                client_request_id=client_request_id,
                provider_request_id=provider_request_id,
            )
        if not isinstance(response_model, str) or not response_model:
            response_model = request.model_id
        if not isinstance(status, str) or not status:
            status = "unknown"
        if status == "failed":
            _raise_failed_response(
                decoded,
                client_request_id=client_request_id,
                provider_request_id=provider_request_id,
            )
        incomplete_reason = _incomplete_reason(decoded) if status == "incomplete" else None
        output_text, refusal_text = _extract_content(
            decoded,
            allow_empty=status == "incomplete" and incomplete_reason is not None,
        )
        return ModelCallResult(
            call_id=request.call_id,
            request_digest=request.digest,
            provider=self.provider,
            response_id=response_id,
            model_id=response_model,
            output_text=output_text,
            status=status,
            latency_ms=int(elapsed_ms),
            usage=_extract_usage(decoded),
            raw_response_sha256=hashlib.sha256(raw).hexdigest(),
            refusal_text=refusal_text,
            incomplete_reason=incomplete_reason,
            client_request_id=client_request_id,
            provider_request_id=provider_request_id,
            provider_processing_ms=provider_processing_ms,
        )
