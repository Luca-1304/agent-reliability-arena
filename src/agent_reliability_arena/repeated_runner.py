from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .config import ExperimentConfig
from .live_requests import PromptCatalog
from .pilot_policy import PilotGateError, PilotPolicy
from .private_pilot import run_private_paired_pilot
from .repeated_plan import (
    RepeatedExperimentPlan,
    TrialPlan,
    build_repeated_experiment_preflight,
)
from .transports import ModelTransport, verify_transport_ledger


_FIXED_ROOT_NAMES = {
    "experiment-plan.json",
    "experiment-preflight.json",
    "experiment-start.json",
    "experiment-checkpoint.json",
    "experiment-summary.json",
    "experiment-abort.json",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(clock: Callable[[], datetime]) -> str:
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("Repeated experiment clock must return a timezone-aware datetime.")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_object(path: Path, name: str) -> dict[str, object]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ValueError(f"{name} must be a regular non-symlink file.")
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{name} is not valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must contain a JSON object.")
    return payload


def _encoded_json(payload: object) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _write_private_json(path: Path, payload: object) -> None:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise ValueError(f"Private experiment artifact must be new and non-symlinked: {target.name}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(_encoded_json(payload))
        handle.flush()
        os.fsync(handle.fileno())
    if os.name != "nt":
        target.chmod(0o600)


def _replace_checkpoint(path: Path, payload: object) -> None:
    target = Path(path)
    if target.is_symlink():
        raise ValueError("Experiment checkpoint must not be a symlink.")
    temporary = target.with_name(".experiment-checkpoint.tmp")
    if temporary.exists() or temporary.is_symlink():
        raise ValueError("Stale experiment checkpoint temporary file exists.")
    _write_private_json(temporary, payload)
    os.replace(temporary, target)
    if os.name != "nt":
        target.chmod(0o600)


def _prepare_root(path: Path) -> tuple[Path, bool]:
    root = Path(path)
    if root.is_symlink():
        raise ValueError("Repeated experiment root must not be a symlink.")
    if root.exists():
        if not root.is_dir():
            raise ValueError("Repeated experiment root must be a directory.")
        return root, not any(root.iterdir())
    root.mkdir(parents=True, mode=0o700)
    if os.name != "nt":
        root.chmod(0o700)
    return root, True


def _trial_config(config: ExperimentConfig, trial: TrialPlan) -> ExperimentConfig:
    return replace(config, seed=trial.seed)


def _trial_policy(template: PilotPolicy, trial: TrialPlan) -> PilotPolicy:
    return replace(template, scenario_ids=(trial.scenario_id,))


def _plan_record(plan: RepeatedExperimentPlan) -> dict[str, object]:
    return {
        "schema_version": "arena-repeated-experiment-plan-record-v1",
        "plan": plan.to_dict(),
        "plan_digest": plan.digest,
    }


def _start_record(
    config: ExperimentConfig,
    catalog: PromptCatalog,
    plan: RepeatedExperimentPlan,
    template: PilotPolicy,
    preflight: dict[str, object],
    clock: Callable[[], datetime],
) -> dict[str, object]:
    return {
        "schema_version": "arena-repeated-experiment-start-v1",
        "status": "started",
        "started_at": _timestamp(clock),
        "plan_digest": plan.digest,
        "preflight_manifest_digest": preflight["manifest_digest"],
        "base_config_digest": config.digest,
        "contract_digest": config.contract.digest,
        "prompt_catalog_digest": catalog.digest,
        "pilot_policy_template_digest": template.digest,
        "provider": plan.provider,
        "model_id": plan.model_id,
        "model_version": plan.model_version,
        "prompt_version": plan.prompt_version,
        "planned_trials": len(plan.trials),
        "stop_on_abort": True,
        "comparative_claim_permitted": False,
        "claims_boundary": (
            "A repeated experiment start record is preregistration evidence, not a model-performance result."
        ),
    }


def _verify_start(
    raw: dict[str, object],
    config: ExperimentConfig,
    catalog: PromptCatalog,
    plan: RepeatedExperimentPlan,
    template: PilotPolicy,
    preflight: dict[str, object],
) -> None:
    expected = {
        "schema_version": "arena-repeated-experiment-start-v1",
        "status": "started",
        "plan_digest": plan.digest,
        "preflight_manifest_digest": preflight["manifest_digest"],
        "base_config_digest": config.digest,
        "contract_digest": config.contract.digest,
        "prompt_catalog_digest": catalog.digest,
        "pilot_policy_template_digest": template.digest,
        "provider": plan.provider,
        "model_id": plan.model_id,
        "model_version": plan.model_version,
        "prompt_version": plan.prompt_version,
        "planned_trials": len(plan.trials),
        "stop_on_abort": True,
        "comparative_claim_permitted": False,
    }
    for key, value in expected.items():
        if raw.get(key) != value:
            raise ValueError(f"Experiment start {key} does not match the reviewed plan.")
    if not isinstance(raw.get("started_at"), str) or not raw.get("started_at"):
        raise ValueError("Experiment start timestamp is invalid.")


def _trial_preflight_by_id(preflight: dict[str, object]) -> dict[str, dict[str, object]]:
    trials = preflight.get("trials")
    if not isinstance(trials, list):
        raise ValueError("Repeated experiment preflight trials are invalid.")
    result: dict[str, dict[str, object]] = {}
    for raw in trials:
        if not isinstance(raw, dict) or not isinstance(raw.get("trial_id"), str):
            raise ValueError("Repeated experiment preflight contains an invalid trial.")
        result[raw["trial_id"]] = raw
    return result


def verify_completed_trial(
    trial_root: Path,
    trial: TrialPlan,
    expected: dict[str, object],
    plan: RepeatedExperimentPlan,
    catalog: PromptCatalog,
) -> dict[str, object]:
    root = Path(trial_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"Completed trial {trial.trial_id} must be a regular directory.")
    if (root / "abort.json").exists():
        raise ValueError(f"Trial {trial.trial_id} is aborted and terminal.")
    summary = _read_object(root / "verification-summary.json", "trial verification summary")
    ledger = verify_transport_ledger(root / "transport-calls.jsonl")
    comparisons = {
        "status": "completed",
        "scenario_id": trial.scenario_id,
        "condition_order": list(trial.condition_order),
        "provider": plan.provider,
        "model_id": plan.model_id,
        "model_version": plan.model_version,
        "prompt_version": plan.prompt_version,
        "config_digest": expected.get("config_digest"),
        "policy_digest": expected.get("policy_digest"),
        "preflight_manifest_digest": expected.get("pilot_preflight_manifest_digest"),
        "contract_digest": plan.contract_digest,
        "prompt_catalog_digest": catalog.digest,
        "comparative_claim_permitted": False,
    }
    for key, value in comparisons.items():
        if summary.get(key) != value:
            raise ValueError(f"Trial {trial.trial_id} {key} does not match its preregistration.")
    if summary.get("ledger") != ledger:
        raise ValueError(f"Trial {trial.trial_id} ledger summary does not match the verified ledger.")
    conditions = summary.get("conditions")
    if not isinstance(conditions, dict) or set(conditions) != {"general", "specialist"}:
        raise ValueError(f"Trial {trial.trial_id} condition results are invalid.")
    for condition in ("general", "specialist"):
        result = conditions.get(condition)
        if not isinstance(result, dict) or not isinstance(result.get("verified_complete"), bool):
            raise ValueError(f"Trial {trial.trial_id} {condition} result is invalid.")
    return summary


def _discover_trial_prefix(
    root: Path,
    plan: RepeatedExperimentPlan,
    preflight: dict[str, object],
    catalog: PromptCatalog,
) -> list[dict[str, object]]:
    expected_names = {trial.trial_id for trial in plan.trials}
    actual_trial_names: set[str] = set()
    for child in root.iterdir():
        if child.name in _FIXED_ROOT_NAMES:
            if child.is_dir():
                raise ValueError(f"Unexpected directory at fixed experiment artifact name: {child.name}")
            continue
        if child.name == ".experiment-checkpoint.tmp":
            raise ValueError("Partial experiment checkpoint temporary file exists.")
        if child.name not in expected_names:
            raise ValueError(f"Repeated experiment root contains unexpected evidence: {child.name}")
        if child.is_symlink() or not child.is_dir():
            raise ValueError(f"Trial evidence must be a regular directory: {child.name}")
        actual_trial_names.add(child.name)

    by_id = _trial_preflight_by_id(preflight)
    completed: list[dict[str, object]] = []
    gap_seen = False
    for trial in plan.trials:
        present = trial.trial_id in actual_trial_names
        if not present:
            gap_seen = True
            continue
        if gap_seen:
            raise ValueError("Existing trial evidence is non-contiguous and therefore partial.")
        trial_root = root / trial.trial_id
        if (trial_root / "abort.json").exists():
            raise ValueError(f"Trial {trial.trial_id} is aborted and the experiment root is terminal.")
        if not (trial_root / "verification-summary.json").is_file():
            raise ValueError(f"Trial {trial.trial_id} contains partial evidence.")
        completed.append(verify_completed_trial(trial_root, trial, by_id[trial.trial_id], plan, catalog))
    return completed


def _checkpoint_payload(
    plan: RepeatedExperimentPlan,
    preflight: dict[str, object],
    completed_trial_ids: list[str],
    clock: Callable[[], datetime],
) -> dict[str, object]:
    next_trial_id = None
    if len(completed_trial_ids) < len(plan.trials):
        next_trial_id = plan.trials[len(completed_trial_ids)].trial_id
    return {
        "schema_version": "arena-repeated-experiment-checkpoint-v1",
        "updated_at": _timestamp(clock),
        "plan_digest": plan.digest,
        "preflight_manifest_digest": preflight["manifest_digest"],
        "completed_trial_ids": list(completed_trial_ids),
        "completed_trials": len(completed_trial_ids),
        "planned_trials": len(plan.trials),
        "next_trial_id": next_trial_id,
    }


def _validate_checkpoint(
    path: Path,
    plan: RepeatedExperimentPlan,
    preflight: dict[str, object],
    completed_trial_ids: list[str],
) -> None:
    if not path.exists():
        return
    raw = _read_object(path, "experiment checkpoint")
    if raw.get("plan_digest") != plan.digest:
        raise ValueError("Experiment checkpoint plan digest mismatch.")
    if raw.get("preflight_manifest_digest") != preflight["manifest_digest"]:
        raise ValueError("Experiment checkpoint preflight digest mismatch.")
    recorded = raw.get("completed_trial_ids")
    if not isinstance(recorded, list) or recorded != completed_trial_ids[: len(recorded)]:
        raise ValueError("Experiment checkpoint does not match the verified completed prefix.")
    if len(recorded) > len(completed_trial_ids):
        raise ValueError("Experiment checkpoint is ahead of verified trial evidence.")


def _progress_payload(
    status: str,
    plan: RepeatedExperimentPlan,
    preflight: dict[str, object],
    completed: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": "arena-repeated-experiment-progress-v1",
        "status": status,
        "plan_digest": plan.digest,
        "preflight_manifest_digest": preflight["manifest_digest"],
        "planned_trials": len(plan.trials),
        "completed_trials": len(completed),
        "aborted_trials": 0,
        "completed_trial_ids": [trial.trial_id for trial in plan.trials[: len(completed)]],
        "comparative_claim_permitted": False,
        "claims_boundary": (
            "A provider-free or partial repeated experiment does not establish representative performance."
        ),
    }


def _summary_payload(
    plan: RepeatedExperimentPlan,
    preflight: dict[str, object],
    completed: list[dict[str, object]],
    clock: Callable[[], datetime],
) -> dict[str, object]:
    trials: list[dict[str, object]] = []
    for trial_plan, summary in zip(plan.trials, completed):
        conditions = summary["conditions"]
        trials.append(
            {
                "trial_id": trial_plan.trial_id,
                "scenario_id": trial_plan.scenario_id,
                "seed": trial_plan.seed,
                "condition_order": list(trial_plan.condition_order),
                "config_digest": summary["config_digest"],
                "policy_digest": summary["policy_digest"],
                "ledger_sha256": summary["ledger"]["ledger_sha256"],
                "logical_model_calls": summary["ledger"]["records"],
                "general_verified_complete": conditions["general"]["verified_complete"],
                "specialist_verified_complete": conditions["specialist"]["verified_complete"],
            }
        )
    return {
        "schema_version": "arena-repeated-experiment-summary-v1",
        "status": "completed",
        "completed_at": _timestamp(clock),
        "plan_digest": plan.digest,
        "preflight_manifest_digest": preflight["manifest_digest"],
        "provider": plan.provider,
        "model_id": plan.model_id,
        "model_version": plan.model_version,
        "prompt_version": plan.prompt_version,
        "planned_trials": len(plan.trials),
        "completed_trials": len(completed),
        "aborted_trials": 0,
        "trials": trials,
        "comparative_claim_permitted": False,
        "claims_boundary": (
            "This summary preserves a repeated paired experiment. It does not establish representative, "
            "causal or universal model performance."
        ),
    }


def run_private_repeated_experiment(
    config: ExperimentConfig,
    catalog: PromptCatalog,
    plan: RepeatedExperimentPlan,
    pilot_policy_template: PilotPolicy,
    transport: ModelTransport,
    root: Path,
    *,
    reviewed_plan_digest: str,
    reviewed_policy_template_digest: str,
    external_execution_approved: bool,
    max_new_trials: int | None = None,
    clock: Callable[[], datetime] = _utc_now,
) -> dict[str, object]:
    if not isinstance(config, ExperimentConfig):
        raise ValueError("'config' must be an ExperimentConfig.")
    if not isinstance(catalog, PromptCatalog):
        raise ValueError("'catalog' must be a PromptCatalog.")
    if not isinstance(plan, RepeatedExperimentPlan):
        raise ValueError("'plan' must be a RepeatedExperimentPlan.")
    if not isinstance(pilot_policy_template, PilotPolicy):
        raise ValueError("'pilot_policy_template' must be a PilotPolicy.")
    if reviewed_plan_digest != plan.digest:
        raise ValueError("The reviewed plan digest does not match the exact repeated experiment plan.")
    if reviewed_policy_template_digest != pilot_policy_template.digest:
        raise ValueError("The reviewed policy template digest does not match the exact PilotPolicy.")
    if not pilot_policy_template.external_execution_enabled:
        raise PilotGateError("External execution is disabled by the reviewed pilot policy template.")
    if not isinstance(external_execution_approved, bool) or not external_execution_approved:
        raise PilotGateError("Explicit external-execution approval is required.")
    if max_new_trials is not None:
        if not isinstance(max_new_trials, int) or isinstance(max_new_trials, bool) or max_new_trials <= 0:
            raise ValueError("'max_new_trials' must be a positive integer when supplied.")

    preflight = build_repeated_experiment_preflight(config, catalog, plan, pilot_policy_template)
    run_root, is_new = _prepare_root(Path(root))
    plan_path = run_root / "experiment-plan.json"
    preflight_path = run_root / "experiment-preflight.json"
    start_path = run_root / "experiment-start.json"
    checkpoint_path = run_root / "experiment-checkpoint.json"
    summary_path = run_root / "experiment-summary.json"
    abort_path = run_root / "experiment-abort.json"

    if is_new:
        _write_private_json(plan_path, _plan_record(plan))
        _write_private_json(preflight_path, preflight)
        _write_private_json(
            start_path,
            _start_record(config, catalog, plan, pilot_policy_template, preflight, clock),
        )
    else:
        if abort_path.exists():
            raise ValueError("The repeated experiment root is terminal after an experiment abort.")
        plan_record = _read_object(plan_path, "experiment plan")
        if plan_record != _plan_record(plan):
            raise ValueError("Existing experiment plan digest or content does not match the reviewed plan digest.")
        if _read_object(preflight_path, "experiment preflight") != preflight:
            raise ValueError("Existing experiment preflight does not match the reviewed plan.")
        _verify_start(
            _read_object(start_path, "experiment start"),
            config,
            catalog,
            plan,
            pilot_policy_template,
            preflight,
        )

    completed = _discover_trial_prefix(run_root, plan, preflight, catalog)
    completed_ids = [trial.trial_id for trial in plan.trials[: len(completed)]]
    _validate_checkpoint(checkpoint_path, plan, preflight, completed_ids)
    _replace_checkpoint(checkpoint_path, _checkpoint_payload(plan, preflight, completed_ids, clock))

    if summary_path.exists():
        if len(completed) != len(plan.trials):
            raise ValueError("Experiment summary exists before all trials are verified.")
        expected_summary = _read_object(summary_path, "experiment summary")
        for key, value in {
            "status": "completed",
            "plan_digest": plan.digest,
            "preflight_manifest_digest": preflight["manifest_digest"],
            "planned_trials": len(plan.trials),
            "completed_trials": len(plan.trials),
            "aborted_trials": 0,
            "comparative_claim_permitted": False,
        }.items():
            if expected_summary.get(key) != value:
                raise ValueError(f"Experiment summary {key} is inconsistent.")
        return expected_summary

    new_trials_started = 0
    by_id = _trial_preflight_by_id(preflight)
    current_trial: TrialPlan | None = None
    try:
        for trial in plan.trials[len(completed) :]:
            if max_new_trials is not None and new_trials_started >= max_new_trials:
                return _progress_payload("paused", plan, preflight, completed)
            current_trial = trial
            trial_config = _trial_config(config, trial)
            trial_policy = _trial_policy(pilot_policy_template, trial)
            trial_summary = run_private_paired_pilot(
                trial_config,
                catalog,
                trial_policy,
                transport,
                run_root / trial.trial_id,
                reviewed_policy_digest=trial_policy.digest,
                external_execution_approved=external_execution_approved,
                condition_order=trial.condition_order,
                clock=clock,
            )
            verified = verify_completed_trial(
                run_root / trial.trial_id,
                trial,
                by_id[trial.trial_id],
                plan,
                catalog,
            )
            if trial_summary != verified:
                raise ValueError(f"Trial {trial.trial_id} returned summary differs from persisted evidence.")
            completed.append(verified)
            completed_ids.append(trial.trial_id)
            new_trials_started += 1
            _replace_checkpoint(
                checkpoint_path,
                _checkpoint_payload(plan, preflight, completed_ids, clock),
            )

        summary = _summary_payload(plan, preflight, completed, clock)
        _write_private_json(summary_path, summary)
        return summary
    except Exception as error:
        if not abort_path.exists():
            _write_private_json(
                abort_path,
                {
                    "schema_version": "arena-repeated-experiment-abort-v1",
                    "status": "aborted",
                    "aborted_at": _timestamp(clock),
                    "plan_digest": plan.digest,
                    "preflight_manifest_digest": preflight["manifest_digest"],
                    "failed_trial_id": current_trial.trial_id if current_trial is not None else None,
                    "completed_trial_ids": list(completed_ids),
                    "completed_trials": len(completed_ids),
                    "planned_trials": len(plan.trials),
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "comparative_claim_permitted": False,
                    "claims_boundary": (
                        "An aborted repeated experiment is execution-state evidence, not a performance result."
                    ),
                },
            )
        raise
