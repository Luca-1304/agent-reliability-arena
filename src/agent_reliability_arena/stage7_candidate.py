from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .config import ExperimentConfig
from .disclosure_export import PriceSource
from .live_requests import PromptCatalog
from .pilot_policy import PilotPolicy, build_pilot_preflight
from .transports.base import canonical_json_sha256


PACKET_SCHEMA = "arena-stage7-disabled-execution-packet-v1"
PRIVACY_GATE_SCHEMA = "arena-stage7-privacy-execution-gate-v1"
_CANDIDATE_FILES = {
    "experiment.json",
    "policy.disabled.json",
    "price-source.json",
    "packet.json",
    "privacy-execution-gate.json",
}
_PACKET_KEYS = {
    "schema_version",
    "prepared_date",
    "provider",
    "model_id",
    "model_version",
    "scenario_ids",
    "config_digest",
    "prompt_catalog_digest",
    "policy_digest",
    "preflight_manifest_digest",
    "price_source_digest",
    "planned_call_ceiling",
    "max_requested_output_tokens",
    "max_reserved_total_tokens",
    "reserved_cost_minor_units",
    "proposed_hard_ceiling_minor_units",
    "conservative_price_bound_minor_units",
    "currency",
    "external_execution_enabled",
    "operator_approved",
    "provider_called",
    "packet_digest",
}
_PRIVACY_GATE_KEYS = {
    "schema_version",
    "issue_number",
    "incident_status",
    "last_verified_date",
    "execution_permitted",
    "rationale",
}
_EXECUTION_PREFLIGHT_INVARIANTS = (
    "provider",
    "model_id",
    "model_version",
    "prompt_version",
    "scenario_ids",
    "planned_call_ceiling",
    "planned_requested_output_tokens",
    "reserved_total_tokens",
    "max_reserved_total_tokens",
    "reserved_cost_minor_units",
    "max_cost_minor_units",
    "currency",
    "calls",
)


def _decode_object(text: str, name: str) -> dict[str, object]:
    def no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{name} contains duplicate key {key!r}.")
            result[key] = value
        return result

    try:
        value = json.loads(text, object_pairs_hook=no_duplicates)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} is not valid JSON.") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{name} must contain a JSON object.")
    return value


def read_stage7_json_object(path: Path, name: str) -> dict[str, object]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ValueError(f"{name} must be a regular non-symlink file.")
    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{name} is not valid UTF-8.") from exc
    return _decode_object(text, name)


def _candidate_root(path: Path, *, require_packet: bool) -> Path:
    root = Path(path)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Stage 7 candidate root must be a regular non-symlink directory.")
    names = {item.name for item in root.iterdir()}
    required = _CANDIDATE_FILES if require_packet else _CANDIDATE_FILES - {"packet.json"}
    if require_packet:
        if names != required:
            raise ValueError("Stage 7 candidate root must contain exactly the documented candidate files.")
    elif not required.issubset(names) or names - required not in (set(), {"packet.json"}):
        raise ValueError("Stage 7 candidate root contains unexpected files.")
    return root


def _catalog(path: Path) -> PromptCatalog:
    return PromptCatalog.from_dict(
        read_stage7_json_object(Path(path), "Stage 7 prompt catalogue")
    )


def _positive_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def _conservative_price_bound(policy: PilotPolicy, price_source: PriceSource) -> int:
    highest_rate = max(
        price_source.input_per_million_minor_units,
        price_source.output_per_million_minor_units,
    )
    numerator = policy.max_reserved_total_tokens * highest_rate
    return (numerator + 999_999) // 1_000_000


def verify_stage7_privacy_gate(path: Path) -> dict[str, object]:
    raw = read_stage7_json_object(Path(path), "Stage 7 privacy execution gate")
    if set(raw) != _PRIVACY_GATE_KEYS:
        raise ValueError("Stage 7 privacy execution gate shape is invalid.")
    if raw.get("schema_version") != PRIVACY_GATE_SCHEMA:
        raise ValueError("Stage 7 privacy execution gate schema_version is invalid.")
    if raw.get("issue_number") != 14:
        raise ValueError("Stage 7 privacy execution gate must reference issue 14.")
    incident_status = raw.get("incident_status")
    if incident_status not in {"open", "closed"}:
        raise ValueError("Stage 7 privacy execution gate incident_status is invalid.")
    execution_permitted = raw.get("execution_permitted")
    if not isinstance(execution_permitted, bool):
        raise ValueError("Stage 7 privacy execution gate execution_permitted must be boolean.")
    if (incident_status == "closed") != execution_permitted:
        raise ValueError("Stage 7 privacy execution gate status and execution permission disagree.")
    verified_date = raw.get("last_verified_date")
    if not isinstance(verified_date, str):
        raise ValueError("Stage 7 privacy execution gate last_verified_date must be a string.")
    try:
        date.fromisoformat(verified_date)
    except ValueError as exc:
        raise ValueError("Stage 7 privacy execution gate last_verified_date is invalid.") from exc
    rationale = raw.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("Stage 7 privacy execution gate rationale must be non-empty.")
    return {
        "status": "verified",
        "issue_number": 14,
        "incident_status": incident_status,
        "last_verified_date": verified_date,
        "execution_permitted": execution_permitted,
        "rationale": rationale.strip(),
    }


def build_stage7_candidate_packet(
    candidate_root: Path,
    catalog_path: Path,
) -> dict[str, object]:
    root = _candidate_root(Path(candidate_root), require_packet=False)
    verify_stage7_privacy_gate(root / "privacy-execution-gate.json")
    config = ExperimentConfig.from_dict(
        read_stage7_json_object(root / "experiment.json", "Stage 7 experiment")
    )
    catalog = _catalog(Path(catalog_path))
    policy = PilotPolicy.from_dict(
        read_stage7_json_object(root / "policy.disabled.json", "Stage 7 disabled policy")
    )
    price_source = PriceSource.from_dict(
        read_stage7_json_object(root / "price-source.json", "Stage 7 price source")
    )

    if policy.provider != "openai-responses":
        raise ValueError("Stage 7 candidate provider must be 'openai-responses'.")
    if config.scenarios != ("success",) or policy.scenario_ids != ("success",):
        raise ValueError("Stage 7 candidate must contain exactly the 'success' scenario.")
    if policy.external_execution_enabled:
        raise ValueError("Stage 7 candidate policy must remain disabled.")
    if price_source.currency != policy.currency:
        raise ValueError("Stage 7 price source currency must match the policy currency.")

    preflight = build_pilot_preflight(config, catalog, policy)
    reserved_cost = _positive_int(
        preflight.get("reserved_cost_minor_units"),
        "Stage 7 preflight reserved_cost_minor_units",
    )
    planned_calls = _positive_int(
        preflight.get("planned_call_ceiling"),
        "Stage 7 preflight planned_call_ceiling",
    )
    if planned_calls != policy.max_calls:
        raise ValueError("Stage 7 planned call ceiling does not match the exact policy reservation.")
    if preflight.get("planned_requested_output_tokens") != policy.max_requested_output_tokens:
        raise ValueError(
            "Stage 7 requested-output-token ceiling must equal the exact preflight maximum."
        )
    if preflight.get("reserved_total_tokens") != policy.max_reserved_total_tokens:
        raise ValueError("Stage 7 total-token reservation must equal the exact policy maximum.")

    conservative_bound = _conservative_price_bound(policy, price_source)
    if conservative_bound > reserved_cost:
        raise ValueError(
            "Stage 7 aggregate monetary reservation is below the conservative token-price bound."
        )
    if reserved_cost > policy.max_cost_minor_units:
        raise ValueError("Stage 7 aggregate monetary reservation exceeds the proposed hard ceiling.")

    price_source_digest = canonical_json_sha256(price_source.to_dict())
    unsigned: dict[str, object] = {
        "schema_version": PACKET_SCHEMA,
        "prepared_date": price_source.source_date,
        "provider": policy.provider,
        "model_id": policy.model_id,
        "model_version": policy.model_version,
        "scenario_ids": list(policy.scenario_ids),
        "config_digest": config.digest,
        "prompt_catalog_digest": catalog.digest,
        "policy_digest": policy.digest,
        "preflight_manifest_digest": preflight["manifest_digest"],
        "price_source_digest": price_source_digest,
        "planned_call_ceiling": planned_calls,
        "max_requested_output_tokens": policy.max_requested_output_tokens,
        "max_reserved_total_tokens": policy.max_reserved_total_tokens,
        "reserved_cost_minor_units": reserved_cost,
        "proposed_hard_ceiling_minor_units": policy.max_cost_minor_units,
        "conservative_price_bound_minor_units": conservative_bound,
        "currency": policy.currency,
        "external_execution_enabled": False,
        "operator_approved": False,
        "provider_called": False,
    }
    return {**unsigned, "packet_digest": canonical_json_sha256(unsigned)}


def _validate_committed_packet(raw: dict[str, object]) -> dict[str, object]:
    if set(raw) != _PACKET_KEYS:
        raise ValueError("Stage 7 packet shape is invalid.")
    if raw.get("schema_version") != PACKET_SCHEMA:
        raise ValueError("Stage 7 packet schema_version is invalid.")
    if raw.get("external_execution_enabled") is not False:
        raise ValueError("Stage 7 packet external_execution_enabled must remain false.")
    if raw.get("operator_approved") is not False:
        raise ValueError("Stage 7 packet operator_approved must remain false.")
    if raw.get("provider_called") is not False:
        raise ValueError("Stage 7 packet provider_called must remain false.")
    supplied_digest = raw.get("packet_digest")
    if not isinstance(supplied_digest, str):
        raise ValueError("Stage 7 packet_digest must be a string.")
    unsigned = dict(raw)
    unsigned.pop("packet_digest")
    if canonical_json_sha256(unsigned) != supplied_digest:
        raise ValueError("Stage 7 packet_digest mismatch.")
    return raw


def verify_stage7_candidate(
    candidate_root: Path,
    catalog_path: Path,
) -> dict[str, object]:
    root = _candidate_root(Path(candidate_root), require_packet=True)
    verify_stage7_privacy_gate(root / "privacy-execution-gate.json")
    committed = _validate_committed_packet(
        read_stage7_json_object(root / "packet.json", "Stage 7 packet")
    )
    expected = build_stage7_candidate_packet(root, Path(catalog_path))
    if committed != expected:
        differing = sorted(
            key for key in _PACKET_KEYS if committed.get(key) != expected.get(key)
        )
        detail = ", ".join(differing) if differing else "unknown"
        raise ValueError(f"Stage 7 packet does not match reconstructed evidence: {detail}.")
    return {
        "status": "verified",
        "model_id": expected["model_id"],
        "model_version": expected["model_version"],
        "scenario_ids": expected["scenario_ids"],
        "config_digest": expected["config_digest"],
        "prompt_catalog_digest": expected["prompt_catalog_digest"],
        "policy_digest": expected["policy_digest"],
        "preflight_manifest_digest": expected["preflight_manifest_digest"],
        "planned_call_ceiling": expected["planned_call_ceiling"],
        "max_requested_output_tokens": expected["max_requested_output_tokens"],
        "max_reserved_total_tokens": expected["max_reserved_total_tokens"],
        "reserved_cost_minor_units": expected["reserved_cost_minor_units"],
        "proposed_hard_ceiling_minor_units": expected["proposed_hard_ceiling_minor_units"],
        "conservative_price_bound_minor_units": expected[
            "conservative_price_bound_minor_units"
        ],
        "currency": expected["currency"],
        "external_execution_enabled": False,
        "operator_approved": False,
        "provider_called": False,
        "packet_digest": expected["packet_digest"],
    }


def verify_stage7_execution_policy(
    candidate_root: Path,
    config_path: Path,
    catalog_path: Path,
    enabled_policy_path: Path,
) -> dict[str, object]:
    root = _candidate_root(Path(candidate_root), require_packet=True)
    candidate = verify_stage7_candidate(root, Path(catalog_path))
    config = ExperimentConfig.from_dict(
        read_stage7_json_object(Path(config_path), "Stage 7 execution config")
    )
    if config.digest != candidate["config_digest"]:
        raise ValueError("Stage 7 execution config does not match the reviewed candidate config.")
    catalog = _catalog(Path(catalog_path))
    disabled = PilotPolicy.from_dict(
        read_stage7_json_object(root / "policy.disabled.json", "Stage 7 disabled policy")
    )
    enabled = PilotPolicy.from_dict(
        read_stage7_json_object(Path(enabled_policy_path), "Stage 7 enabled policy")
    )

    expected_enabled = disabled.to_dict()
    if expected_enabled["external_execution_enabled"] is not False:
        raise ValueError("Stage 7 reviewed candidate policy is not disabled.")
    expected_enabled["external_execution_enabled"] = True
    actual_enabled = enabled.to_dict()
    if actual_enabled != expected_enabled:
        differing = sorted(
            key
            for key in expected_enabled
            if actual_enabled.get(key) != expected_enabled.get(key)
        )
        detail = ", ".join(differing) if differing else "unknown"
        raise ValueError(
            "Stage 7 enabled policy differs from the reviewed candidate outside the single "
            f"execution-enable flag: {detail}."
        )

    disabled_preflight = build_pilot_preflight(config, catalog, disabled)
    enabled_preflight = build_pilot_preflight(config, catalog, enabled)
    for key in _EXECUTION_PREFLIGHT_INVARIANTS:
        if enabled_preflight.get(key) != disabled_preflight.get(key):
            raise ValueError(
                f"Stage 7 enabled preflight differs from the reviewed candidate at {key}."
            )
    if enabled_preflight.get("external_execution_enabled") is not True:
        raise ValueError("Stage 7 enabled preflight did not preserve execution enablement.")

    return {
        "status": "verified",
        "candidate_packet_digest": candidate["packet_digest"],
        "config_digest": config.digest,
        "prompt_catalog_digest": catalog.digest,
        "policy_digest": enabled.digest,
        "preflight_manifest_digest": enabled_preflight["manifest_digest"],
        "provider": enabled.provider,
        "model_id": enabled.model_id,
        "model_version": enabled.model_version,
        "scenario_ids": list(enabled.scenario_ids),
        "planned_call_ceiling": enabled_preflight["planned_call_ceiling"],
        "max_requested_output_tokens": enabled.max_requested_output_tokens,
        "max_reserved_total_tokens": enabled.max_reserved_total_tokens,
        "reserved_cost_minor_units": enabled_preflight["reserved_cost_minor_units"],
        "max_cost_minor_units": enabled.max_cost_minor_units,
        "currency": enabled.currency,
        "external_execution_enabled": True,
        "provider_called": False,
    }
