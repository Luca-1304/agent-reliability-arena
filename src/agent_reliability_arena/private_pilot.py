from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ExperimentConfig
from .live_orchestration import LiveGeneralOrchestrator, LiveSpecialistOrchestrator
from .live_requests import PromptCatalog
from .pilot_policy import (
    PilotExecutionGate,
    PilotGateError,
    PilotPolicy,
    build_pilot_preflight,
)
from .transports import ModelTransport, RecordingTransport, verify_transport_ledger


_CONDITION_ORDERS = {
    ("general", "specialist"),
    ("specialist", "general"),
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(clock: Callable[[], datetime]) -> str:
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("Private pilot clock must return a timezone-aware datetime.")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalise_condition_order(value: object) -> tuple[str, str]:
    if not isinstance(value, tuple) or value not in _CONDITION_ORDERS:
        raise ValueError(
            "'condition_order' must be exactly ('general', 'specialist') or "
            "('specialist', 'general')."
        )
    return value


def _prepare_private_root(path: Path) -> Path:
    root = Path(path)
    if root.is_symlink():
        raise ValueError("Private pilot run directory must not be a symlink.")
    if root.exists():
        if not root.is_dir():
            raise ValueError("Private pilot run path must be a directory.")
        if any(root.iterdir()):
            raise ValueError("Private pilot run directory must be empty.")
    else:
        root.mkdir(parents=True, mode=0o700)
    if os.name != "nt":
        root.chmod(0o700)
    return root


def _private_directory(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"Private evidence directory must not be a symlink: {path}")
    path.mkdir(parents=True, exist_ok=False, mode=0o700)
    if os.name != "nt":
        path.chmod(0o700)


def _write_private_json(path: Path, payload: object) -> None:
    target = Path(path)
    if target.is_symlink():
        raise ValueError(f"Private evidence path must not be a symlink: {target}")
    encoded = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    if os.name != "nt":
        target.chmod(0o600)


def _ledger_summary(path: Path) -> dict[str, object] | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    return verify_transport_ledger(path)


def _abort_payload(
    *,
    stage: str,
    error: BaseException,
    gate: PilotExecutionGate | None,
    ledger_path: Path,
    condition_order: tuple[str, str],
    clock: Callable[[], datetime],
) -> dict[str, object]:
    ledger: dict[str, object] | None = None
    ledger_verification_error: str | None = None
    try:
        ledger = _ledger_summary(ledger_path)
    except Exception as exc:
        ledger_verification_error = f"{type(exc).__name__}: {exc}"
    return {
        "schema_version": "arena-private-pilot-abort-v1",
        "status": "aborted",
        "aborted_at": _timestamp(clock),
        "stage": stage,
        "condition_order": list(condition_order),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "gate": dict(gate.snapshot()) if gate is not None else None,
        "ledger": ledger,
        "ledger_verification_error": ledger_verification_error,
        "claims_boundary": "An aborted private pilot is evidence of execution state, not model performance.",
    }


def run_private_paired_pilot(
    config: ExperimentConfig,
    catalog: PromptCatalog,
    policy: PilotPolicy,
    transport: ModelTransport,
    root: Path,
    *,
    reviewed_policy_digest: str,
    external_execution_approved: bool,
    condition_order: tuple[str, str] = ("general", "specialist"),
    clock: Callable[[], datetime] = _utc_now,
) -> dict[str, object]:
    if not isinstance(config, ExperimentConfig):
        raise ValueError("'config' must be an ExperimentConfig.")
    if not isinstance(catalog, PromptCatalog):
        raise ValueError("'catalog' must be a PromptCatalog.")
    if not isinstance(policy, PilotPolicy):
        raise ValueError("'policy' must be a PilotPolicy.")
    if len(policy.scenario_ids) != 1:
        raise ValueError("The minimal private pilot requires exactly one scenario.")
    condition_order = _normalise_condition_order(condition_order)
    if not policy.external_execution_enabled:
        raise PilotGateError("External execution is disabled by the reviewed pilot policy.")
    if not isinstance(external_execution_approved, bool) or not external_execution_approved:
        raise PilotGateError("Explicit external-execution approval is required.")

    preflight = build_pilot_preflight(config, catalog, policy)
    run_root = _prepare_private_root(Path(root))
    ledger_path = run_root / "transport-calls.jsonl"
    gate: PilotExecutionGate | None = None
    stage = "initialise"

    try:
        _write_private_json(run_root / "preflight.json", preflight)
        _write_private_json(run_root / "policy.json", policy.to_dict())
        _write_private_json(
            run_root / "run-start.json",
            {
                "schema_version": "arena-private-pilot-start-v1",
                "status": "started",
                "started_at": _timestamp(clock),
                "condition_order": list(condition_order),
                "scenario_id": policy.scenario_ids[0],
                "provider": policy.provider,
                "model_id": policy.model_id,
                "model_version": policy.model_version,
                "prompt_version": policy.prompt_version,
                "policy_digest": policy.digest,
                "preflight_manifest_digest": preflight["manifest_digest"],
                "config_digest": config.digest,
                "contract_digest": config.contract.digest,
                "prompt_catalog_digest": catalog.digest,
                "external_execution_approved": True,
                "claims_boundary": "One private paired pilot cannot establish representative performance.",
            },
        )

        gate = PilotExecutionGate(
            transport,
            policy,
            reviewed_policy_digest=reviewed_policy_digest,
            external_execution_approved=external_execution_approved,
            allowed_calls=preflight["calls"],
        )
        recorded = RecordingTransport(gate, ledger_path, clock=clock)
        scenario_id = policy.scenario_ids[0]
        results: dict[str, Any] = {}

        for condition in condition_order:
            stage = condition
            condition_directory = run_root / condition
            _private_directory(condition_directory)
            if condition == "general":
                execution = LiveGeneralOrchestrator(recorded).run(
                    config,
                    catalog,
                    scenario_id,
                    condition_directory / "sandbox",
                )
            else:
                execution = LiveSpecialistOrchestrator(recorded).run(
                    config,
                    catalog,
                    scenario_id,
                    condition_directory / "sandbox",
                )
            _write_private_json(condition_directory / "result.json", execution.to_dict())
            results[condition] = execution

        general = results["general"]
        specialist = results["specialist"]

        stage = "ledger-verification"
        ledger = verify_transport_ledger(ledger_path)
        expected_records = general.logical_model_calls + specialist.logical_model_calls
        if ledger["records"] != expected_records:
            raise RuntimeError("Verified ledger record count does not match completed role calls.")
        if ledger["errors"] != 0:
            raise RuntimeError("A completed private pilot must not contain an unhandled ledger error record.")

        stage = "finalise"
        summary: dict[str, object] = {
            "schema_version": "arena-private-pilot-summary-v1",
            "status": "completed",
            "completed_at": _timestamp(clock),
            "scenario_id": scenario_id,
            "condition_order": list(condition_order),
            "provider": policy.provider,
            "model_id": policy.model_id,
            "model_version": policy.model_version,
            "prompt_version": policy.prompt_version,
            "policy_digest": policy.digest,
            "preflight_manifest_digest": preflight["manifest_digest"],
            "config_digest": config.digest,
            "contract_digest": config.contract.digest,
            "prompt_catalog_digest": catalog.digest,
            "conditions": {
                "general": general.to_dict(),
                "specialist": specialist.to_dict(),
            },
            "gate": dict(gate.snapshot()),
            "ledger": ledger,
            "comparative_claim_permitted": False,
            "claims_boundary": (
                "This summary proves only that one controlled paired pilot completed with preserved "
                "evidence. It does not establish representative model performance."
            ),
        }
        _write_private_json(run_root / "verification-summary.json", summary)
        return summary
    except Exception as error:
        try:
            if not (run_root / "abort.json").exists():
                _write_private_json(
                    run_root / "abort.json",
                    _abort_payload(
                        stage=stage,
                        error=error,
                        gate=gate,
                        ledger_path=ledger_path,
                        condition_order=condition_order,
                        clock=clock,
                    ),
                )
        except Exception:
            pass
        raise
