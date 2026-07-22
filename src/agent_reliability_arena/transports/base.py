from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{name}' must be a non-empty string.")
    return value.strip()


def _required_content(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{name}' must be a non-empty string.")
    return value


def _non_negative_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"'{name}' must be a non-negative integer.")
    return value


def canonical_json_sha256(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ModelCallRequest:
    call_id: str
    condition: str
    role: str
    model_id: str
    model_version: str
    prompt_version: str
    instructions: str
    input_text: str
    max_output_tokens: int
    seed: int
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "call_id",
            "condition",
            "role",
            "model_id",
            "model_version",
            "prompt_version",
        ):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        object.__setattr__(self, "instructions", _required_content(self.instructions, "instructions"))
        object.__setattr__(self, "input_text", _required_content(self.input_text, "input_text"))
        object.__setattr__(self, "max_output_tokens", _non_negative_int(self.max_output_tokens, "max_output_tokens"))
        if self.max_output_tokens == 0:
            raise ValueError("'max_output_tokens' must be greater than zero.")
        object.__setattr__(self, "seed", _non_negative_int(self.seed, "seed"))
        if not isinstance(self.metadata, dict):
            raise ValueError("'metadata' must be a dictionary of strings.")
        normalised: dict[str, str] = {}
        for key, value in self.metadata.items():
            normalised[_required_text(key, "metadata key")] = _required_text(value, "metadata value")
        object.__setattr__(self, "metadata", normalised)

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "condition": self.condition,
            "role": self.role,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "prompt_version": self.prompt_version,
            "instructions": self.instructions,
            "input_text": self.input_text,
            "max_output_tokens": self.max_output_tokens,
            "seed": self.seed,
            "metadata": dict(self.metadata),
        }

    @property
    def digest(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0

    def __post_init__(self) -> None:
        for name in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cached_input_tokens",
            "reasoning_tokens",
        ):
            object.__setattr__(self, name, _non_negative_int(getattr(self, name), name))
        if self.total_tokens < self.input_tokens + self.output_tokens:
            raise ValueError("'total_tokens' cannot be smaller than input_tokens + output_tokens.")

    def to_dict(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "reasoning_tokens": self.reasoning_tokens,
        }


@dataclass(frozen=True)
class ModelCallResult:
    call_id: str
    request_digest: str
    provider: str
    response_id: str
    model_id: str
    output_text: str
    status: str
    latency_ms: int
    usage: ModelUsage
    raw_response_sha256: str
    refusal_text: str | None = None
    provider_request_id: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "call_id",
            "request_digest",
            "provider",
            "response_id",
            "model_id",
            "status",
            "raw_response_sha256",
        ):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        if not isinstance(self.output_text, str):
            raise ValueError("'output_text' must be a string.")
        if self.refusal_text is not None:
            object.__setattr__(self, "refusal_text", _required_content(self.refusal_text, "refusal_text"))
        if not self.output_text and self.refusal_text is None:
            raise ValueError("A model result must contain output_text or refusal_text.")
        object.__setattr__(self, "latency_ms", _non_negative_int(self.latency_ms, "latency_ms"))
        if self.provider_request_id is not None:
            object.__setattr__(
                self,
                "provider_request_id",
                _required_text(self.provider_request_id, "provider_request_id"),
            )
        if not isinstance(self.usage, ModelUsage):
            raise ValueError("'usage' must be a ModelUsage instance.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "request_digest": self.request_digest,
            "provider": self.provider,
            "response_id": self.response_id,
            "model_id": self.model_id,
            "output_text": self.output_text,
            "refusal_text": self.refusal_text,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "usage": self.usage.to_dict(),
            "raw_response_sha256": self.raw_response_sha256,
            "provider_request_id": self.provider_request_id,
        }


class TransportError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        category: str,
        retryable: bool,
        status_code: int | None = None,
        provider_request_id: str | None = None,
    ) -> None:
        super().__init__(_required_content(message, "message"))
        self.category = _required_text(category, "category")
        self.retryable = bool(retryable)
        self.status_code = status_code
        self.provider_request_id = provider_request_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": str(self),
            "category": self.category,
            "retryable": self.retryable,
            "status_code": self.status_code,
            "provider_request_id": self.provider_request_id,
        }


@runtime_checkable
class ModelTransport(Protocol):
    provider: str

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        ...
