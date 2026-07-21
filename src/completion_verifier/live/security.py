from __future__ import annotations

import json
import re
from typing import Any, Iterable

_SECRET_KEYS = {
    "api_key",
    "openai_api_key",
    "authorization",
    "headers",
    "request_headers",
    "client_secret",
    "secret",
    "access_token",
}
_SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)authorization\s*[:=]?\s*bearer\s+\S+"),
    re.compile(r"(?i)bearer\s+\S+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{4,}\b"),
)


class LiveRunError(RuntimeError):
    """Raised for invalid or exhausted live-run orchestration."""

def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{name}' must be a non-empty string.")
    if "\x00" in value:
        raise ValueError(f"'{name}' contains a NUL byte.")
    return value.strip()

def _plain_json(value: object, name: str) -> Any:
    try:
        encoded = json.dumps(value, allow_nan=False, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{name}' must be JSON-serialisable.") from exc
    return json.loads(encoded)

def _walk_keys(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_keys(item)

def reject_secret_like_keys(value: object, name: str) -> None:
    for key in _walk_keys(value):
        if key.strip().lower() in _SECRET_KEYS:
            raise ValueError(f"'{name}' contains a secret-like field '{key}'.")

def redact_error_text(value: object) -> str:
    text = str(value)
    for pattern in _SECRET_VALUE_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text[:500]

def contract_instructions(config: "LiveRunConfig") -> str:
    return (
        config.developer_instructions
        + "\nExact contracted relative path: "
        + json.dumps(config.contract.path, ensure_ascii=False)
        + "\nExact contracted UTF-8 content: "
        + json.dumps(config.contract.content, ensure_ascii=False)
    )

def write_file_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "name": "write_file",
        "description": (
            "Write the exact contracted UTF-8 content to the exact contracted "
            "relative sandbox path."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    }
