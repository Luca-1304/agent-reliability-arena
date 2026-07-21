from __future__ import annotations

import json
from typing import Any

from .models import ResponseRecord, ResponseRequest, redact_error_text


def _plain(value: object) -> Any:
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _plain(model_dump(mode="json"))
        except TypeError:
            return _plain(model_dump())
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _plain(to_dict())
    try:
        return json.loads(json.dumps(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"OpenAI response contains a non-serialisable value of type {type(value).__name__}."
        ) from exc


class OpenAIResponsesTransport:
    name = "openai-responses-sdk"
    version = "1"

    def __init__(self, client: object | None = None):
        if client is None:
            try:
                from openai import OpenAI
            except (ImportError, ModuleNotFoundError) as exc:
                raise RuntimeError(
                    "The optional OpenAI SDK is not installed. Install "
                    "agent-completion-verifier[openai] for live execution."
                ) from exc
            client = OpenAI(max_retries=0)
        self._client = client
        self._request_index = 0

    def create(self, request: ResponseRequest) -> ResponseRecord:
        request_index = self._request_index
        self._request_index += 1
        try:
            response = self._client.responses.create(**request.to_dict())
        except Exception as exc:  # SDK/network boundary; no automatic retry
            return ResponseRecord(
                response_id=None,
                model=request.model,
                status="transport_error",
                incomplete_details=None,
                output_items=(),
                output_text=None,
                usage={},
                request_index=request_index,
                transport_error={
                    "type": type(exc).__name__,
                    "message": redact_error_text(exc),
                },
                raw={
                    "status": "transport_error",
                    "error_type": type(exc).__name__,
                },
            )

        raw = _plain(response)
        if not isinstance(raw, dict):
            raise ValueError("OpenAI SDK response must serialise to an object.")
        output_text = raw.get("output_text")
        if output_text is None:
            candidate = getattr(response, "output_text", None)
            if isinstance(candidate, str):
                output_text = candidate
        output = raw.get("output", [])
        if not isinstance(output, list):
            output = []
        usage = raw.get("usage", {})
        if not isinstance(usage, dict):
            usage = {}
        incomplete_details = raw.get("incomplete_details")
        if incomplete_details is not None and not isinstance(incomplete_details, dict):
            incomplete_details = {"value": str(incomplete_details)}
        return ResponseRecord(
            response_id=raw.get("id"),
            model=raw.get("model", request.model),
            status=raw.get("status", "completed"),
            incomplete_details=incomplete_details,
            output_items=tuple(output),
            output_text=output_text if isinstance(output_text, str) else None,
            usage=usage,
            request_index=request_index,
            transport_error=None,
            raw=raw,
        )
