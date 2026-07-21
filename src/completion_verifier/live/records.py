from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..models import Case, Evaluation
from ..sandbox.models import FileObservation, SourceToolReport
from .config import LiveRunConfig, ResponseRequest
from .security import _plain_json, _required_text, reject_secret_like_keys

@dataclass(frozen=True)
class ResponseRecord:
    response_id: str | None
    model: str | None
    status: str
    incomplete_details: dict[str, Any] | None
    output_items: tuple[dict[str, Any], ...]
    output_text: str | None
    usage: dict[str, Any]
    request_index: int
    transport_error: dict[str, str] | None
    raw: dict[str, Any]

    def __post_init__(self) -> None:
        if self.response_id is not None:
            object.__setattr__(self, "response_id", _required_text(self.response_id, "response_id"))
        if self.model is not None:
            object.__setattr__(self, "model", _required_text(self.model, "model"))
        object.__setattr__(self, "status", _required_text(self.status, "status"))
        if not isinstance(self.request_index, int) or isinstance(self.request_index, bool) or self.request_index < 0:
            raise ValueError("'request_index' must be a non-negative integer.")
        if self.output_text is not None and not isinstance(self.output_text, str):
            raise ValueError("'output_text' must be a string or null.")
        output_items = tuple(_plain_json(item, "output_items") for item in self.output_items)
        usage = _plain_json(self.usage, "usage")
        raw = _plain_json(self.raw, "raw")
        if not isinstance(usage, dict) or not isinstance(raw, dict):
            raise ValueError("Response usage and raw snapshot must be objects.")
        reject_secret_like_keys(raw, "response raw snapshot")
        if self.incomplete_details is not None:
            details = _plain_json(self.incomplete_details, "incomplete_details")
            if not isinstance(details, dict):
                raise ValueError("'incomplete_details' must be an object or null.")
            object.__setattr__(self, "incomplete_details", details)
        if self.transport_error is not None:
            error = _plain_json(self.transport_error, "transport_error")
            if not isinstance(error, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in error.items()
            ):
                raise ValueError("'transport_error' must map strings to strings.")
            object.__setattr__(self, "transport_error", error)
        object.__setattr__(self, "output_items", output_items)
        object.__setattr__(self, "usage", usage)
        object.__setattr__(self, "raw", raw)

    @classmethod
    def from_dict(cls, raw: object) -> "ResponseRecord":
        if not isinstance(raw, dict):
            raise ValueError("Response fixture must be a JSON object.")
        snapshot = raw.get("raw")
        if snapshot is None:
            snapshot = {
                "id": raw.get("response_id") or raw.get("id"),
                "model": raw.get("model"),
                "status": raw.get("status", "completed"),
                "incomplete_details": raw.get("incomplete_details"),
                "output": raw.get("output_items", raw.get("output", [])),
                "output_text": raw.get("output_text"),
                "usage": raw.get("usage", {}),
                "store": False,
            }
        return cls(
            response_id=raw.get("response_id", raw.get("id")),
            model=raw.get("model"),
            status=raw.get("status", "completed"),
            incomplete_details=raw.get("incomplete_details"),
            output_items=tuple(raw.get("output_items", raw.get("output", []))),
            output_text=raw.get("output_text"),
            usage=raw.get("usage", {}),
            request_index=raw.get("request_index", 0),
            transport_error=raw.get("transport_error"),
            raw=snapshot,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id": self.response_id,
            "model": self.model,
            "status": self.status,
            "incomplete_details": self.incomplete_details,
            "output_items": [dict(item) for item in self.output_items],
            "output_text": self.output_text,
            "usage": dict(self.usage),
            "request_index": self.request_index,
            "transport_error": self.transport_error,
            "raw": dict(self.raw),
        }

@dataclass(frozen=True)
class FunctionCallRecord:
    request_index: int
    call_id: str | None
    name: str | None
    arguments: str | None
    accepted: bool
    validation_error: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_index": self.request_index,
            "call_id": self.call_id,
            "name": self.name,
            "arguments": self.arguments,
            "accepted": self.accepted,
            "validation_error": self.validation_error,
        }

@dataclass(frozen=True)
class ToolOutputRecord:
    request_index: int
    call_id: str
    executed: bool
    output: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_index": self.request_index,
            "call_id": self.call_id,
            "executed": self.executed,
            "output": dict(self.output),
        }

    def input_item(self) -> dict[str, Any]:
        return {
            "type": "function_call_output",
            "call_id": self.call_id,
            "output": json.dumps(
                self.output,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
        }

@dataclass(frozen=True)
class LiveRunResult:
    config: LiveRunConfig
    requests: tuple[ResponseRequest, ...]
    responses: tuple[ResponseRecord, ...]
    function_calls: tuple[FunctionCallRecord, ...]
    tool_outputs: tuple[ToolOutputRecord, ...]
    source_report: SourceToolReport
    observation: FileObservation
    case: Case
    evaluation: Evaluation
    completion_claimed: bool
    final_summary: str | None
    usage: dict[str, Any]
    errors: tuple[dict[str, Any], ...]
    transport_name: str
    transport_version: str

    @property
    def error_codes(self) -> tuple[str, ...]:
        return tuple(str(error.get("code", "unknown")) for error in self.errors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.config.run_id,
            "model": self.config.model,
            "status": self.evaluation.status.value,
            "completion_claimed": self.completion_claimed,
            "matches_contract": self.observation.matches_contract,
            "final_summary": self.final_summary,
            "request_count": len(self.requests),
            "function_call_count": len(self.function_calls),
            "executed_tool_count": sum(item.executed for item in self.tool_outputs),
            "error_codes": list(self.error_codes),
            "usage": self.usage,
            "transport": self.transport_name,
            "transport_version": self.transport_version,
        }
