from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from completion_verifier.adapters import canonical_json_sha256
from completion_verifier.sandbox.models import FileWriteContract, required_text
from completion_verifier.sandbox.scenarios import SCENARIO_IDS


CONDITIONS = ("general", "specialist")


def _positive_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"'{name}' must be a non-negative integer.")
    return value


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str
    generated_at: str
    model_id: str
    model_version: str
    prompt_version: str
    seed: int
    task: str
    scenarios: tuple[str, ...]
    conditions: tuple[str, ...]
    max_mutation_attempts: int
    contract: FileWriteContract
    schema_version: str = "1"

    def __post_init__(self) -> None:
        for field_name in (
            "experiment_id",
            "generated_at",
            "model_id",
            "model_version",
            "prompt_version",
            "task",
            "schema_version",
        ):
            object.__setattr__(self, field_name, required_text(getattr(self, field_name), field_name))
        if self.schema_version != "1":
            raise ValueError(f"Unsupported schema_version '{self.schema_version}'.")
        object.__setattr__(self, "seed", _positive_int(self.seed, "seed"))
        if not isinstance(self.scenarios, tuple) or not self.scenarios:
            raise ValueError("'scenarios' must be a non-empty tuple.")
        if len(self.scenarios) != len(set(self.scenarios)):
            raise ValueError("Duplicate scenario identifiers are not allowed.")
        unknown = [scenario for scenario in self.scenarios if scenario not in SCENARIO_IDS]
        if unknown:
            raise ValueError("Unknown scenario: " + ", ".join(unknown))
        if self.conditions != CONDITIONS:
            raise ValueError("'conditions' must be exactly ['general', 'specialist'] in that order.")
        if (
            not isinstance(self.max_mutation_attempts, int)
            or isinstance(self.max_mutation_attempts, bool)
            or self.max_mutation_attempts not in {1, 2}
        ):
            raise ValueError("'max_mutation_attempts' must be 1 or 2.")
        if not isinstance(self.contract, FileWriteContract):
            raise ValueError("'contract' must be a FileWriteContract.")

    @classmethod
    def from_dict(cls, raw: object) -> "ExperimentConfig":
        if not isinstance(raw, dict):
            raise ValueError("Experiment configuration must be a JSON object.")
        scenarios_raw = raw.get("scenarios")
        conditions_raw = raw.get("conditions")
        if not isinstance(scenarios_raw, list):
            raise ValueError("'scenarios' must be a list.")
        if not isinstance(conditions_raw, list):
            raise ValueError("'conditions' must be a list.")
        return cls(
            experiment_id=raw.get("experiment_id"),
            generated_at=raw.get("generated_at"),
            model_id=raw.get("model_id"),
            model_version=raw.get("model_version"),
            prompt_version=raw.get("prompt_version"),
            seed=raw.get("seed"),
            task=raw.get("task"),
            scenarios=tuple(required_text(item, "scenario") for item in scenarios_raw),
            conditions=tuple(required_text(item, "condition") for item in conditions_raw),
            max_mutation_attempts=raw.get("max_mutation_attempts"),
            contract=FileWriteContract.from_dict(raw.get("contract")),
            schema_version=raw.get("schema_version", "1"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "generated_at": self.generated_at,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "prompt_version": self.prompt_version,
            "seed": self.seed,
            "task": self.task,
            "scenarios": list(self.scenarios),
            "conditions": list(self.conditions),
            "max_mutation_attempts": self.max_mutation_attempts,
            "contract": self.contract.to_dict(),
            "schema_version": self.schema_version,
        }

    @property
    def digest(self) -> str:
        return canonical_json_sha256(self.to_dict())

    def fairness_fingerprint(self, condition: str) -> dict[str, Any]:
        if condition not in self.conditions:
            raise ValueError(f"Unknown condition '{condition}'.")
        return {
            "model_id": self.model_id,
            "model_version": self.model_version,
            "prompt_version": self.prompt_version,
            "seed": self.seed,
            "task": self.task,
            "scenarios": list(self.scenarios),
            "max_mutation_attempts": self.max_mutation_attempts,
            "contract_digest": self.contract.digest,
        }
