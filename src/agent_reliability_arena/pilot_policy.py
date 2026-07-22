from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from .config import ExperimentConfig
from .live_requests import PromptCatalog, build_live_request_preflight
from .transports.base import ModelCallRequest, ModelCallResult, ModelTransport, canonical_json_sha256


_POLICY_FIELDS = {
    "schema_version",
    "provider",
    "model_id",
    "model_version",
    "prompt_version",
    "scenario_ids",
    "max_calls",
    "max_requested_output_tokens",
    "reserved_total_tokens_per_call",
    "max_reserved_total_tokens",
    "currency",
    "reserved_cost_per_call_minor_units",
    "max_cost_minor_units",
    "external_execution_enabled",
}


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{name}' must be a non-empty string.")
    return value.strip()


def _positive_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"'{name}' must be a positive integer.")
    return value


def _required_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"'{name}' must be a boolean.")
    return value


@dataclass(frozen=True)
class PilotPolicy:
    provider: str
    model_id: str
    model_version: str
    prompt_version: str
    scenario_ids: tuple[str, ...]
    max_calls: int
    max_requested_output_tokens: int
    reserved_total_tokens_per_call: int
    max_reserved_total_tokens: int
    currency: str
    reserved_cost_per_call_minor_units: int
    max_cost_minor_units: int
    external_execution_enabled: bool
    schema_version: str = "1"

    def __post_init__(self) -> None:
        for name in ("provider", "model_id", "model_version", "prompt_version", "schema_version"):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        if self.schema_version != "1":
            raise ValueError(f"Unsupported pilot policy schema_version '{self.schema_version}'.")
        if not isinstance(self.scenario_ids, tuple) or not self.scenario_ids:
            raise ValueError("'scenario_ids' must be a non-empty list of unique scenario IDs.")
        normalised = tuple(_required_text(value, "scenario_ids item") for value in self.scenario_ids)
        if len(set(normalised)) != len(normalised):
            raise ValueError("'scenario_ids' must contain unique values.")
        object.__setattr__(self, "scenario_ids", normalised)
        for name in (
            "max_calls",
            "max_requested_output_tokens",
            "reserved_total_tokens_per_call",
            "max_reserved_total_tokens",
            "reserved_cost_per_call_minor_units",
            "max_cost_minor_units",
        ):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name))
        if self.max_reserved_total_tokens < self.reserved_total_tokens_per_call:
            raise ValueError("'max_reserved_total_tokens' cannot be smaller than one per-call reservation.")
        if self.max_cost_minor_units < self.reserved_cost_per_call_minor_units:
            raise ValueError("'max_cost_minor_units' cannot be smaller than one per-call reservation.")
        currency = _required_text(self.currency, "currency").upper()
        if len(currency) != 3 or not currency.isalpha() or not currency.isascii():
            raise ValueError("'currency' must be a three-letter ASCII code.")
        object.__setattr__(self, "currency", currency)
        object.__setattr__(
            self,
            "external_execution_enabled",
            _required_bool(self.external_execution_enabled, "external_execution_enabled"),
        )

    @classmethod
    def from_dict(cls, raw: object) -> "PilotPolicy":
        if not isinstance(raw, dict) or set(raw) != _POLICY_FIELDS:
            raise ValueError("Pilot policy must contain exactly the documented release-candidate fields.")
        scenario_ids = raw.get("scenario_ids")
        if not isinstance(scenario_ids, list):
            raise ValueError("'scenario_ids' must be a list.")
        return cls(
            schema_version=raw.get("schema_version"),
            provider=raw.get("provider"),
            model_id=raw.get("model_id"),
            model_version=raw.get("model_version"),
            prompt_version=raw.get("prompt_version"),
            scenario_ids=tuple(scenario_ids),
            max_calls=raw.get("max_calls"),
            max_requested_output_tokens=raw.get("max_requested_output_tokens"),
            reserved_total_tokens_per_call=raw.get("reserved_total_tokens_per_call"),
            max_reserved_total_tokens=raw.get("max_reserved_total_tokens"),
            currency=raw.get("currency"),
            reserved_cost_per_call_minor_units=raw.get("reserved_cost_per_call_minor_units"),
            max_cost_minor_units=raw.get("max_cost_minor_units"),
            external_execution_enabled=raw.get("external_execution_enabled"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "provider": self.provider,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "prompt_version": self.prompt_version,
            "scenario_ids": list(self.scenario_ids),
            "max_calls": self.max_calls,
            "max_requested_output_tokens": self.max_requested_output_tokens,
            "reserved_total_tokens_per_call": self.reserved_total_tokens_per_call,
            "max_reserved_total_tokens": self.max_reserved_total_tokens,
            "currency": self.currency,
            "reserved_cost_per_call_minor_units": self.reserved_cost_per_call_minor_units,
            "max_cost_minor_units": self.max_cost_minor_units,
            "external_execution_enabled": self.external_execution_enabled,
        }

    @property
    def digest(self) -> str:
        return canonical_json_sha256(self.to_dict())


def build_pilot_preflight(
    config: ExperimentConfig,
    catalog: PromptCatalog,
    policy: PilotPolicy,
) -> dict[str, object]:
    if not isinstance(config, ExperimentConfig):
        raise ValueError("'config' must be an ExperimentConfig.")
    if not isinstance(catalog, PromptCatalog):
        raise ValueError("'catalog' must be a PromptCatalog.")
    if not isinstance(policy, PilotPolicy):
        raise ValueError("'policy' must be a PilotPolicy.")
    for name in ("model_id", "model_version", "prompt_version"):
        if getattr(policy, name) != getattr(config, name):
            raise ValueError(f"Pilot policy {name} does not match ExperimentConfig.{name}.")
    unknown = [scenario_id for scenario_id in policy.scenario_ids if scenario_id not in config.scenarios]
    if unknown:
        raise ValueError(f"Pilot policy scenario_ids contain unknown values: {', '.join(unknown)}")

    full = build_live_request_preflight(config, catalog)
    selected = [scenario for scenario in full["scenarios"] if scenario["scenario_id"] in policy.scenario_ids]
    calls = [call for scenario in selected for call in scenario["calls"]]
    planned_call_ceiling = len(calls)
    planned_output_tokens = sum(int(call["max_output_tokens"]) for call in calls)
    reserved_total_tokens = planned_call_ceiling * policy.reserved_total_tokens_per_call
    reserved_cost = planned_call_ceiling * policy.reserved_cost_per_call_minor_units

    if policy.max_calls != planned_call_ceiling:
        raise ValueError(
            f"Pilot policy max_calls must equal the preflight call ceiling ({planned_call_ceiling})."
        )
    if policy.max_requested_output_tokens < planned_output_tokens:
        raise ValueError(
            "Pilot policy max_requested_output_tokens is below the preflight maximum."
        )
    if policy.max_reserved_total_tokens < reserved_total_tokens:
        raise ValueError("Pilot policy max_reserved_total_tokens is below the required reservation.")
    if policy.max_cost_minor_units < reserved_cost:
        raise ValueError("Pilot policy max_cost_minor_units is below the required reservation.")

    unsigned: dict[str, object] = {
        "schema_version": "arena-pilot-preflight-v1",
        "provider_called": False,
        "external_execution_enabled": policy.external_execution_enabled,
        "policy_digest": policy.digest,
        "config_digest": config.digest,
        "contract_digest": config.contract.digest,
        "prompt_catalog_digest": catalog.digest,
        "provider": policy.provider,
        "model_id": policy.model_id,
        "model_version": policy.model_version,
        "prompt_version": policy.prompt_version,
        "scenario_ids": list(policy.scenario_ids),
        "planned_call_ceiling": planned_call_ceiling,
        "planned_requested_output_tokens": planned_output_tokens,
        "reserved_total_tokens": reserved_total_tokens,
        "max_reserved_total_tokens": policy.max_reserved_total_tokens,
        "reserved_cost_minor_units": reserved_cost,
        "max_cost_minor_units": policy.max_cost_minor_units,
        "currency": policy.currency,
        "calls": calls,
    }
    manifest = dict(unsigned)
    manifest["manifest_digest"] = canonical_json_sha256(unsigned)
    return manifest


class PilotGateError(RuntimeError):
    pass


class PilotExecutionGate:
    def __init__(
        self,
        transport: ModelTransport,
        policy: PilotPolicy,
        *,
        reviewed_policy_digest: str,
        external_execution_approved: bool,
    ) -> None:
        if not isinstance(policy, PilotPolicy):
            raise ValueError("'policy' must be a PilotPolicy.")
        if not isinstance(reviewed_policy_digest, str) or reviewed_policy_digest != policy.digest:
            raise ValueError("The reviewed policy digest does not match the exact PilotPolicy.")
        if not isinstance(external_execution_approved, bool):
            raise ValueError("'external_execution_approved' must be a boolean.")
        provider = getattr(transport, "provider", None)
        if provider != policy.provider:
            raise ValueError("Transport provider does not match the PilotPolicy provider.")
        self.transport = transport
        self.policy = policy
        self.external_execution_approved = external_execution_approved
        self.calls_started = 0
        self.requested_output_tokens_reserved = 0
        self.total_tokens_reserved = 0
        self.cost_minor_units_reserved = 0
        self.observed_total_tokens = 0

    @property
    def provider(self) -> str:
        return self.policy.provider

    def _check_request(self, request: ModelCallRequest) -> None:
        if not isinstance(request, ModelCallRequest):
            raise PilotGateError("Pilot execution requires a ModelCallRequest.")
        for name in ("model_id", "model_version", "prompt_version"):
            if getattr(request, name) != getattr(self.policy, name):
                raise PilotGateError(f"Request {name} is outside the reviewed pilot policy.")
        scenario_id = request.metadata.get("scenario_id")
        if scenario_id not in self.policy.scenario_ids:
            raise PilotGateError("Request scenario_id is outside the reviewed pilot policy.")

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        if not self.policy.external_execution_enabled:
            raise PilotGateError("External execution is disabled by the reviewed pilot policy.")
        if not self.external_execution_approved:
            raise PilotGateError("Explicit external-execution approval is required.")
        self._check_request(request)

        next_calls = self.calls_started + 1
        next_output_tokens = self.requested_output_tokens_reserved + request.max_output_tokens
        next_total_tokens = self.total_tokens_reserved + self.policy.reserved_total_tokens_per_call
        next_cost = self.cost_minor_units_reserved + self.policy.reserved_cost_per_call_minor_units
        if next_calls > self.policy.max_calls:
            raise PilotGateError("Pilot max_calls ceiling would be exceeded.")
        if next_output_tokens > self.policy.max_requested_output_tokens:
            raise PilotGateError("Pilot max_requested_output_tokens ceiling would be exceeded.")
        if next_total_tokens > self.policy.max_reserved_total_tokens:
            raise PilotGateError("Pilot max_reserved_total_tokens ceiling would be exceeded.")
        if next_cost > self.policy.max_cost_minor_units:
            raise PilotGateError("Pilot max_cost_minor_units ceiling would be exceeded.")

        self.calls_started = next_calls
        self.requested_output_tokens_reserved = next_output_tokens
        self.total_tokens_reserved = next_total_tokens
        self.cost_minor_units_reserved = next_cost
        result = self.transport.complete(request)
        self.observed_total_tokens += result.usage.total_tokens
        return result

    def snapshot(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "policy_digest": self.policy.digest,
                "provider": self.policy.provider,
                "calls_started": self.calls_started,
                "requested_output_tokens_reserved": self.requested_output_tokens_reserved,
                "total_tokens_reserved": self.total_tokens_reserved,
                "cost_minor_units_reserved": self.cost_minor_units_reserved,
                "currency": self.policy.currency,
                "observed_total_tokens": self.observed_total_tokens,
            }
        )
