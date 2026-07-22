from __future__ import annotations

import re
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Mapping

from .config import ExperimentConfig
from .live_requests import PromptCatalog
from .pilot_policy import PilotPolicy, build_pilot_preflight
from .transports.base import canonical_json_sha256


_CONDITION_ORDERS = {
    ("general", "specialist"),
    ("specialist", "general"),
}
_TRIAL_ID = re.compile(r"^trial-[0-9]{4,}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{name}' must be a non-empty string.")
    return value.strip()


def _digest(value: object, name: str) -> str:
    text = _required_text(value, name)
    if not _HEX64.fullmatch(text):
        raise ValueError(f"'{name}' must be a lowercase SHA-256 digest.")
    return text


def _non_negative_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"'{name}' must be a non-negative integer.")
    return value


def _positive_int(value: object, name: str) -> int:
    number = _non_negative_int(value, name)
    if number == 0:
        raise ValueError(f"'{name}' must be greater than zero.")
    return number


@dataclass(frozen=True)
class TrialPlan:
    trial_id: str
    scenario_id: str
    seed: int
    condition_order: tuple[str, str]

    def __post_init__(self) -> None:
        trial_id = _required_text(self.trial_id, "trial_id")
        if not _TRIAL_ID.fullmatch(trial_id):
            raise ValueError("'trial_id' must use the canonical trial-0001 form.")
        object.__setattr__(self, "trial_id", trial_id)
        object.__setattr__(self, "scenario_id", _required_text(self.scenario_id, "scenario_id"))
        object.__setattr__(self, "seed", _non_negative_int(self.seed, "seed"))
        if not isinstance(self.condition_order, tuple) or self.condition_order not in _CONDITION_ORDERS:
            raise ValueError(
                "'condition_order' must be exactly ('general', 'specialist') or "
                "('specialist', 'general')."
            )

    @classmethod
    def from_dict(cls, raw: object) -> "TrialPlan":
        fields = {"trial_id", "scenario_id", "seed", "condition_order"}
        if not isinstance(raw, dict) or set(raw) != fields:
            raise ValueError("Trial plan must contain exactly the documented fields.")
        order = raw.get("condition_order")
        if not isinstance(order, list) or len(order) != 2:
            raise ValueError("'condition_order' must be a two-item list.")
        return cls(
            trial_id=raw.get("trial_id"),
            scenario_id=raw.get("scenario_id"),
            seed=raw.get("seed"),
            condition_order=(order[0], order[1]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "trial_id": self.trial_id,
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "condition_order": list(self.condition_order),
        }


@dataclass(frozen=True)
class RepeatedExperimentPlan:
    provider: str
    model_id: str
    model_version: str
    prompt_version: str
    base_config_digest: str
    contract_digest: str
    prompt_catalog_digest: str
    pilot_policy_template_digest: str
    trials: tuple[TrialPlan, ...]
    stop_on_abort: bool = True
    schema_version: str = "1"

    def __post_init__(self) -> None:
        for name in ("provider", "model_id", "model_version", "prompt_version", "schema_version"):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        if self.schema_version != "1":
            raise ValueError(f"Unsupported repeated experiment schema_version '{self.schema_version}'.")
        for name in (
            "base_config_digest",
            "contract_digest",
            "prompt_catalog_digest",
            "pilot_policy_template_digest",
        ):
            object.__setattr__(self, name, _digest(getattr(self, name), name))
        if not isinstance(self.stop_on_abort, bool) or not self.stop_on_abort:
            raise ValueError("Repeated experiment schema version 1 requires stop_on_abort=true.")
        if not isinstance(self.trials, tuple) or len(self.trials) < 2:
            raise ValueError("A repeated experiment requires at least two trials.")
        if not all(isinstance(trial, TrialPlan) for trial in self.trials):
            raise ValueError("'trials' must contain only TrialPlan instances.")
        trial_ids = [trial.trial_id for trial in self.trials]
        if len(trial_ids) != len(set(trial_ids)):
            raise ValueError("Repeated experiment trial_id values must be unique.")
        seeds = [trial.seed for trial in self.trials]
        if len(seeds) != len(set(seeds)):
            raise ValueError("Repeated experiment seed values must be unique.")
        for scenario_id, counts in self.order_counts.items():
            if abs(counts["general_first"] - counts["specialist_first"]) > 1:
                raise ValueError(f"Condition-order imbalance exceeds one for scenario '{scenario_id}'.")

    @classmethod
    def from_dict(cls, raw: object) -> "RepeatedExperimentPlan":
        fields = {
            "schema_version",
            "provider",
            "model_id",
            "model_version",
            "prompt_version",
            "base_config_digest",
            "contract_digest",
            "prompt_catalog_digest",
            "pilot_policy_template_digest",
            "trials",
            "stop_on_abort",
        }
        if not isinstance(raw, dict) or set(raw) != fields:
            raise ValueError("Repeated experiment plan must contain exactly the documented fields.")
        trials = raw.get("trials")
        if not isinstance(trials, list):
            raise ValueError("'trials' must be a list.")
        return cls(
            schema_version=raw.get("schema_version"),
            provider=raw.get("provider"),
            model_id=raw.get("model_id"),
            model_version=raw.get("model_version"),
            prompt_version=raw.get("prompt_version"),
            base_config_digest=raw.get("base_config_digest"),
            contract_digest=raw.get("contract_digest"),
            prompt_catalog_digest=raw.get("prompt_catalog_digest"),
            pilot_policy_template_digest=raw.get("pilot_policy_template_digest"),
            trials=tuple(TrialPlan.from_dict(trial) for trial in trials),
            stop_on_abort=raw.get("stop_on_abort"),
        )

    @property
    def order_counts(self) -> Mapping[str, Mapping[str, int]]:
        counts: dict[str, dict[str, int]] = {}
        for trial in self.trials:
            scenario = counts.setdefault(
                trial.scenario_id,
                {"general_first": 0, "specialist_first": 0},
            )
            key = "general_first" if trial.condition_order[0] == "general" else "specialist_first"
            scenario[key] += 1
        return MappingProxyType(
            {
                scenario_id: MappingProxyType(dict(values))
                for scenario_id, values in counts.items()
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "provider": self.provider,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "prompt_version": self.prompt_version,
            "base_config_digest": self.base_config_digest,
            "contract_digest": self.contract_digest,
            "prompt_catalog_digest": self.prompt_catalog_digest,
            "pilot_policy_template_digest": self.pilot_policy_template_digest,
            "trials": [trial.to_dict() for trial in self.trials],
            "stop_on_abort": self.stop_on_abort,
        }

    @property
    def digest(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _validate_sources(
    config: ExperimentConfig,
    catalog: PromptCatalog,
    template: PilotPolicy,
) -> None:
    if not isinstance(config, ExperimentConfig):
        raise ValueError("'config' must be an ExperimentConfig.")
    if not isinstance(catalog, PromptCatalog):
        raise ValueError("'catalog' must be a PromptCatalog.")
    if not isinstance(template, PilotPolicy):
        raise ValueError("'pilot_policy_template' must be a PilotPolicy.")
    if len(template.scenario_ids) != 1:
        raise ValueError("The pilot policy template must contain exactly one scenario ID.")
    for name in ("model_id", "model_version", "prompt_version"):
        if getattr(template, name) != getattr(config, name):
            raise ValueError(f"Pilot policy template {name} does not match ExperimentConfig.{name}.")
    if catalog.prompt_version != config.prompt_version:
        raise ValueError("Prompt catalogue prompt_version does not match the experiment configuration.")


def build_counterbalanced_plan(
    config: ExperimentConfig,
    catalog: PromptCatalog,
    pilot_policy_template: PilotPolicy,
    *,
    scenario_ids: tuple[str, ...],
    repetitions_per_scenario: int,
    starting_seed: int,
) -> RepeatedExperimentPlan:
    _validate_sources(config, catalog, pilot_policy_template)
    if not isinstance(scenario_ids, tuple) or not scenario_ids:
        raise ValueError("'scenario_ids' must be a non-empty tuple.")
    normalised_scenarios = tuple(_required_text(value, "scenario_id") for value in scenario_ids)
    if len(normalised_scenarios) != len(set(normalised_scenarios)):
        raise ValueError("Repeated experiment scenario IDs must be unique.")
    unknown = [scenario_id for scenario_id in normalised_scenarios if scenario_id not in config.scenarios]
    if unknown:
        raise ValueError("Repeated experiment contains unknown scenario IDs: " + ", ".join(unknown))
    repetitions = _positive_int(repetitions_per_scenario, "repetitions_per_scenario")
    seed = _non_negative_int(starting_seed, "starting_seed")

    trials: list[TrialPlan] = []
    for repetition_index in range(repetitions):
        order = (
            ("general", "specialist")
            if repetition_index % 2 == 0
            else ("specialist", "general")
        )
        for scenario_id in normalised_scenarios:
            trial_number = len(trials) + 1
            trials.append(
                TrialPlan(
                    trial_id=f"trial-{trial_number:04d}",
                    scenario_id=scenario_id,
                    seed=seed + len(trials),
                    condition_order=order,
                )
            )

    return RepeatedExperimentPlan(
        provider=pilot_policy_template.provider,
        model_id=config.model_id,
        model_version=config.model_version,
        prompt_version=config.prompt_version,
        base_config_digest=config.digest,
        contract_digest=config.contract.digest,
        prompt_catalog_digest=catalog.digest,
        pilot_policy_template_digest=pilot_policy_template.digest,
        trials=tuple(trials),
    )


def _validate_plan_sources(
    config: ExperimentConfig,
    catalog: PromptCatalog,
    plan: RepeatedExperimentPlan,
    template: PilotPolicy,
) -> None:
    _validate_sources(config, catalog, template)
    if not isinstance(plan, RepeatedExperimentPlan):
        raise ValueError("'plan' must be a RepeatedExperimentPlan.")
    comparisons = {
        "provider": template.provider,
        "model_id": config.model_id,
        "model_version": config.model_version,
        "prompt_version": config.prompt_version,
        "base_config_digest": config.digest,
        "contract_digest": config.contract.digest,
        "prompt_catalog_digest": catalog.digest,
        "pilot_policy_template_digest": template.digest,
    }
    for name, expected in comparisons.items():
        if getattr(plan, name) != expected:
            label = "template digest" if name == "pilot_policy_template_digest" else name
            raise ValueError(f"Repeated experiment {label} does not match its source.")
    unknown = sorted({trial.scenario_id for trial in plan.trials if trial.scenario_id not in config.scenarios})
    if unknown:
        raise ValueError("Repeated experiment contains unknown scenario IDs: " + ", ".join(unknown))


def build_repeated_experiment_preflight(
    config: ExperimentConfig,
    catalog: PromptCatalog,
    plan: RepeatedExperimentPlan,
    pilot_policy_template: PilotPolicy,
) -> dict[str, object]:
    _validate_plan_sources(config, catalog, plan, pilot_policy_template)

    trials: list[dict[str, object]] = []
    planned_call_ceiling = 0
    planned_requested_output_tokens = 0
    reserved_total_tokens = 0
    max_reserved_total_tokens = 0
    reserved_cost_minor_units = 0
    max_cost_minor_units = 0

    for trial in plan.trials:
        trial_config = replace(config, seed=trial.seed)
        trial_policy = replace(pilot_policy_template, scenario_ids=(trial.scenario_id,))
        pilot = build_pilot_preflight(trial_config, catalog, trial_policy)
        planned_call_ceiling += int(pilot["planned_call_ceiling"])
        planned_requested_output_tokens += int(pilot["planned_requested_output_tokens"])
        reserved_total_tokens += int(pilot["reserved_total_tokens"])
        max_reserved_total_tokens += trial_policy.max_reserved_total_tokens
        reserved_cost_minor_units += int(pilot["reserved_cost_minor_units"])
        max_cost_minor_units += trial_policy.max_cost_minor_units
        trials.append(
            {
                "trial_id": trial.trial_id,
                "scenario_id": trial.scenario_id,
                "seed": trial.seed,
                "condition_order": list(trial.condition_order),
                "config_digest": trial_config.digest,
                "policy_digest": trial_policy.digest,
                "pilot_preflight_manifest_digest": pilot["manifest_digest"],
                "planned_call_ceiling": pilot["planned_call_ceiling"],
                "planned_requested_output_tokens": pilot["planned_requested_output_tokens"],
                "reserved_total_tokens": pilot["reserved_total_tokens"],
                "max_reserved_total_tokens": trial_policy.max_reserved_total_tokens,
                "reserved_cost_minor_units": pilot["reserved_cost_minor_units"],
                "max_cost_minor_units": trial_policy.max_cost_minor_units,
                "calls": pilot["calls"],
            }
        )

    unsigned: dict[str, object] = {
        "schema_version": "arena-repeated-experiment-preflight-v1",
        "provider_called": False,
        "external_execution_enabled": pilot_policy_template.external_execution_enabled,
        "plan_digest": plan.digest,
        "base_config_digest": config.digest,
        "contract_digest": config.contract.digest,
        "prompt_catalog_digest": catalog.digest,
        "pilot_policy_template_digest": pilot_policy_template.digest,
        "provider": plan.provider,
        "model_id": plan.model_id,
        "model_version": plan.model_version,
        "prompt_version": plan.prompt_version,
        "planned_trials": len(plan.trials),
        "planned_call_ceiling": planned_call_ceiling,
        "planned_requested_output_tokens": planned_requested_output_tokens,
        "reserved_total_tokens": reserved_total_tokens,
        "max_reserved_total_tokens": max_reserved_total_tokens,
        "reserved_cost_minor_units": reserved_cost_minor_units,
        "max_cost_minor_units": max_cost_minor_units,
        "currency": pilot_policy_template.currency,
        "stop_on_abort": plan.stop_on_abort,
        "order_counts": {
            scenario_id: dict(values) for scenario_id, values in plan.order_counts.items()
        },
        "trials": trials,
    }
    manifest = dict(unsigned)
    manifest["manifest_digest"] = canonical_json_sha256(unsigned)
    return manifest
