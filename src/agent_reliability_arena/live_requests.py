from __future__ import annotations

import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from .config import ExperimentConfig
from .transports.base import ModelCallRequest, canonical_json_sha256

ROLE_NAMES = (
    "general",
    "strategist",
    "operator",
    "auditor",
    "recovery",
    "synthesiser",
)

_CALL_GRAMMAR = (
    ("general", "general", 1, True),
    ("specialist", "strategist", 1, True),
    ("specialist", "operator", 1, True),
    ("specialist", "auditor", 1, True),
    ("specialist", "recovery", 1, False),
    ("specialist", "operator", 2, False),
    ("specialist", "auditor", 2, False),
    ("specialist", "synthesiser", 1, True),
)

_ALLOWED_ATTEMPTS = {
    (condition, role): frozenset(
        attempt_number
        for candidate_condition, candidate_role, attempt_number, _required in _CALL_GRAMMAR
        if candidate_condition == condition and candidate_role == role
    )
    for condition, role, _attempt_number, _required in _CALL_GRAMMAR
}


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{name}' must be a non-empty string.")
    return value.strip()


def _required_content(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{name}' must be a non-empty string.")
    return value


def _positive_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"'{name}' must be a positive integer.")
    return value


def _validate_json_value(value: object, path: str = "role_payload") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError(f"'{path}' must contain finite JSON numbers.")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"'{path}' object keys must be strings.")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise ValueError(f"'{path}' must contain only JSON-compatible values.")


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


@dataclass(frozen=True)
class RolePrompt:
    instructions: str
    max_output_tokens: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "instructions", _required_content(self.instructions, "instructions"))
        object.__setattr__(
            self,
            "max_output_tokens",
            _positive_int(self.max_output_tokens, "max_output_tokens"),
        )

    @classmethod
    def from_dict(cls, raw: object) -> "RolePrompt":
        if not isinstance(raw, dict) or set(raw) != {"instructions", "max_output_tokens"}:
            raise ValueError("Each role prompt must contain exactly 'instructions' and 'max_output_tokens'.")
        return cls(
            instructions=raw.get("instructions"),
            max_output_tokens=raw.get("max_output_tokens"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "instructions": self.instructions,
            "max_output_tokens": self.max_output_tokens,
        }


@dataclass(frozen=True)
class PromptCatalog:
    prompt_version: str
    roles: Mapping[str, RolePrompt]
    schema_version: str = "1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "prompt_version", _required_text(self.prompt_version, "prompt_version"))
        object.__setattr__(self, "schema_version", _required_text(self.schema_version, "schema_version"))
        if self.schema_version != "1":
            raise ValueError(f"Unsupported prompt catalogue schema_version '{self.schema_version}'.")
        if not isinstance(self.roles, Mapping) or set(self.roles) != set(ROLE_NAMES):
            raise ValueError("'roles' must contain exactly: " + ", ".join(ROLE_NAMES))
        ordered: dict[str, RolePrompt] = {}
        for role in ROLE_NAMES:
            prompt = self.roles[role]
            if not isinstance(prompt, RolePrompt):
                raise ValueError(f"Role '{role}' must be a RolePrompt.")
            ordered[role] = prompt
        object.__setattr__(self, "roles", MappingProxyType(ordered))

    @classmethod
    def from_dict(cls, raw: object) -> "PromptCatalog":
        if not isinstance(raw, dict) or set(raw) != {"schema_version", "prompt_version", "roles"}:
            raise ValueError("Prompt catalogue must contain exactly schema_version, prompt_version, and roles.")
        roles_raw = raw.get("roles")
        if not isinstance(roles_raw, dict) or set(roles_raw) != set(ROLE_NAMES):
            raise ValueError("'roles' must contain exactly: " + ", ".join(ROLE_NAMES))
        return cls(
            prompt_version=raw.get("prompt_version"),
            roles={role: RolePrompt.from_dict(roles_raw[role]) for role in ROLE_NAMES},
            schema_version=raw.get("schema_version"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "prompt_version": self.prompt_version,
            "roles": {role: self.roles[role].to_dict() for role in ROLE_NAMES},
        }

    @property
    def digest(self) -> str:
        return canonical_json_sha256(self.to_dict())


class LiveRequestFactory:
    def __init__(self, config: ExperimentConfig, catalog: PromptCatalog) -> None:
        if not isinstance(config, ExperimentConfig):
            raise ValueError("'config' must be an ExperimentConfig.")
        if not isinstance(catalog, PromptCatalog):
            raise ValueError("'catalog' must be a PromptCatalog.")
        if catalog.prompt_version != config.prompt_version:
            raise ValueError(
                "Prompt catalogue prompt_version does not match ExperimentConfig.prompt_version."
            )
        self.config = config
        self.catalog = catalog

    def build(
        self,
        *,
        condition: str,
        role: str,
        scenario_id: str,
        attempt_number: int,
        role_payload: dict[str, object],
    ) -> ModelCallRequest:
        condition = _required_text(condition, "condition")
        role = _required_text(role, "role")
        scenario_id = _required_text(scenario_id, "scenario_id")
        if scenario_id not in self.config.scenarios:
            raise ValueError(f"Unknown scenario_id '{scenario_id}'.")
        allowed_attempts = _ALLOWED_ATTEMPTS.get((condition, role))
        if allowed_attempts is None:
            raise ValueError(f"Role '{role}' is not permitted for condition '{condition}'.")
        if not isinstance(attempt_number, int) or isinstance(attempt_number, bool) or attempt_number not in allowed_attempts:
            raise ValueError(
                f"Attempt {attempt_number!r} is not permitted for {condition}/{role}."
            )
        if not isinstance(role_payload, dict):
            raise ValueError("'role_payload' must be a JSON object.")
        _validate_json_value(role_payload)
        canonical_role_payload = json.loads(_canonical_json(role_payload))
        input_payload = {
            "attempt_number": attempt_number,
            "config_digest": self.config.digest,
            "contract": self.config.contract.to_dict(),
            "experiment_id": self.config.experiment_id,
            "role_payload": canonical_role_payload,
            "scenario_id": scenario_id,
            "task": self.config.task,
        }
        prompt = self.catalog.roles[role]
        call_id = (
            f"{self.config.experiment_id}--{condition}--{scenario_id}--{role}--{attempt_number}"
        )
        return ModelCallRequest(
            call_id=call_id,
            condition=condition,
            role=role,
            model_id=self.config.model_id,
            model_version=self.config.model_version,
            prompt_version=self.config.prompt_version,
            instructions=prompt.instructions,
            input_text=_canonical_json(input_payload),
            max_output_tokens=prompt.max_output_tokens,
            seed=self.config.seed,
            metadata={
                "experiment_id": self.config.experiment_id,
                "config_digest": self.config.digest,
                "contract_digest": self.config.contract.digest,
                "prompt_catalog_digest": self.catalog.digest,
                "scenario_id": scenario_id,
                "condition": condition,
                "role": role,
                "attempt_number": str(attempt_number),
            },
        )


def build_live_request_preflight(
    config: ExperimentConfig,
    catalog: PromptCatalog,
) -> dict[str, object]:
    factory = LiveRequestFactory(config, catalog)
    scenarios: list[dict[str, object]] = []
    for scenario_id in config.scenarios:
        calls: list[dict[str, object]] = []
        for condition, role, attempt_number, required in _CALL_GRAMMAR:
            prompt = catalog.roles[role]
            calls.append(
                {
                    "call_id": (
                        f"{config.experiment_id}--{condition}--{scenario_id}--{role}--{attempt_number}"
                    ),
                    "condition": condition,
                    "role": role,
                    "attempt_number": attempt_number,
                    "required": required,
                    "model_id": config.model_id,
                    "model_version": config.model_version,
                    "prompt_version": config.prompt_version,
                    "max_output_tokens": prompt.max_output_tokens,
                }
            )
        scenarios.append({"scenario_id": scenario_id, "calls": calls})

    unsigned: dict[str, object] = {
        "schema_version": "1",
        "experiment_id": config.experiment_id,
        "config_digest": config.digest,
        "contract_digest": config.contract.digest,
        "prompt_catalog_digest": catalog.digest,
        "held_constant": config.fairness_fingerprint("general"),
        "model_id": config.model_id,
        "model_version": config.model_version,
        "prompt_version": config.prompt_version,
        "scenarios": scenarios,
    }
    manifest = dict(unsigned)
    manifest["manifest_digest"] = canonical_json_sha256(unsigned)
    assert factory.catalog.digest == catalog.digest
    return manifest
