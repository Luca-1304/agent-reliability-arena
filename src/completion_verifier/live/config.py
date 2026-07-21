from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ..adapters import canonical_json_sha256
from ..sandbox.models import FileWriteContract
from .security import (
    _plain_json,
    _required_text,
    contract_instructions,
    reject_secret_like_keys,
    write_file_tool,
)

@dataclass(frozen=True)
class LiveRunConfig:
    run_id: str
    provider: str
    model: str
    prompt_version: str
    developer_instructions: str
    task: str
    contract: FileWriteContract
    max_tool_rounds: int
    max_output_tokens: int
    generated_at: str
    schema_version: str = "1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_text(self.run_id, "run_id"))
        object.__setattr__(self, "provider", _required_text(self.provider, "provider"))
        if self.provider != "openai":
            raise ValueError("'provider' must be 'openai' in this release.")
        object.__setattr__(self, "model", _required_text(self.model, "model"))
        object.__setattr__(self, "prompt_version", _required_text(self.prompt_version, "prompt_version"))
        object.__setattr__(
            self,
            "developer_instructions",
            _required_text(self.developer_instructions, "developer_instructions"),
        )
        object.__setattr__(self, "task", _required_text(self.task, "task"))
        object.__setattr__(self, "generated_at", _required_text(self.generated_at, "generated_at"))
        object.__setattr__(self, "schema_version", _required_text(self.schema_version, "schema_version"))
        if self.schema_version != "1":
            raise ValueError(f"Unsupported live schema_version '{self.schema_version}'.")
        if not isinstance(self.max_tool_rounds, int) or isinstance(self.max_tool_rounds, bool) or not 1 <= self.max_tool_rounds <= 4:
            raise ValueError("'max_tool_rounds' must be an integer from 1 to 4.")
        if not isinstance(self.max_output_tokens, int) or isinstance(self.max_output_tokens, bool) or not 1 <= self.max_output_tokens <= 8192:
            raise ValueError("'max_output_tokens' must be an integer from 1 to 8192.")
        if not isinstance(self.contract, FileWriteContract):
            raise ValueError("'contract' must be a FileWriteContract.")

    @classmethod
    def from_dict(cls, raw: object) -> "LiveRunConfig":
        if not isinstance(raw, dict):
            raise ValueError("Live run configuration must be a JSON object.")
        return cls(
            run_id=raw.get("run_id"),
            provider=raw.get("provider"),
            model=raw.get("model"),
            prompt_version=raw.get("prompt_version"),
            developer_instructions=raw.get("developer_instructions"),
            task=raw.get("task"),
            contract=FileWriteContract.from_dict(raw.get("contract")),
            max_tool_rounds=raw.get("max_tool_rounds", 2),
            max_output_tokens=raw.get("max_output_tokens", 512),
            generated_at=raw.get("generated_at"),
            schema_version=raw.get("schema_version", "1"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "provider": self.provider,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "developer_instructions": self.developer_instructions,
            "task": self.task,
            "contract": self.contract.to_dict(),
            "max_tool_rounds": self.max_tool_rounds,
            "max_output_tokens": self.max_output_tokens,
            "generated_at": self.generated_at,
            "schema_version": self.schema_version,
        }

    @property
    def digest(self) -> str:
        return canonical_json_sha256(self.to_dict())

    def with_model(self, model: str) -> "LiveRunConfig":
        return replace(self, model=_required_text(model, "model"))

@dataclass(frozen=True)
class ResponseRequest:
    model: str
    input_items: tuple[dict[str, Any], ...]
    instructions: str
    tools: tuple[dict[str, Any], ...]
    tool_choice: str
    parallel_tool_calls: bool
    store: bool
    max_output_tokens: int
    metadata: dict[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "model", _required_text(self.model, "model"))
        object.__setattr__(self, "instructions", _required_text(self.instructions, "instructions"))
        if self.store is not False:
            raise ValueError("Live runner requests must set store=False.")
        if self.parallel_tool_calls is not False:
            raise ValueError("Live runner requests must disable parallel tool calls.")
        if self.tool_choice not in {"required", "none"}:
            raise ValueError("'tool_choice' must be 'required' or 'none'.")
        if not isinstance(self.max_output_tokens, int) or isinstance(self.max_output_tokens, bool) or self.max_output_tokens <= 0:
            raise ValueError("'max_output_tokens' must be a positive integer.")
        input_items = tuple(_plain_json(item, "input_items") for item in self.input_items)
        tools = tuple(_plain_json(tool, "tools") for tool in self.tools)
        metadata = _plain_json(self.metadata, "metadata")
        if not isinstance(metadata, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in metadata.items()
        ):
            raise ValueError("'metadata' must map strings to strings.")
        reject_secret_like_keys((input_items, tools, metadata), "request")
        object.__setattr__(self, "input_items", input_items)
        object.__setattr__(self, "tools", tools)
        object.__setattr__(self, "metadata", metadata)

    @classmethod
    def first(cls, config: LiveRunConfig) -> "ResponseRequest":
        return cls(
            model=config.model,
            input_items=(
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": config.task},
                    ],
                },
            ),
            instructions=contract_instructions(config),
            tools=(write_file_tool(),),
            tool_choice="required",
            parallel_tool_calls=False,
            store=False,
            max_output_tokens=config.max_output_tokens,
            metadata={
                "run_id": config.run_id,
                "prompt_version": config.prompt_version,
                "config_digest": config.digest,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "input": [dict(item) for item in self.input_items],
            "instructions": self.instructions,
            "tools": [dict(tool) for tool in self.tools],
            "tool_choice": self.tool_choice,
            "parallel_tool_calls": self.parallel_tool_calls,
            "store": self.store,
            "max_output_tokens": self.max_output_tokens,
            "metadata": dict(self.metadata),
        }
