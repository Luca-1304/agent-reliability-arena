from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

try:
    from scripts.ci.reliability_policy import ReliabilityPolicy, load_policy
    from scripts.ci.workflow_contract import WorkflowContract, WorkflowStep, read_workflow_contract
except ModuleNotFoundError:  # Direct execution from scripts/ci.
    from reliability_policy import ReliabilityPolicy, load_policy  # type: ignore[no-redef]
    from workflow_contract import WorkflowContract, WorkflowStep, read_workflow_contract  # type: ignore[no-redef]


_SHA_ACTION_RE = re.compile(r"^[^@\s]+@[0-9a-fA-F]{40}$")
_DOCKER_DIGEST_RE = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-fA-F]{64}$")
_PERMISSION_RANK = {"none": 0, "read": 1, "write": 2}
_DEFAULT_WORKFLOWS = {"deep": Path(".github/workflows/fifteen-pass-verification.yml")}


@dataclass(frozen=True, order=True)
class PolicyViolation:
    code: str
    location: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "location": self.location, "message": self.message}


def _permission_violations(
    declared: Mapping[str, str],
    maximum: Mapping[str, str],
    *,
    location: str,
) -> list[PolicyViolation]:
    violations: list[PolicyViolation] = []
    if not declared:
        violations.append(
            PolicyViolation(
                "permissions-missing",
                location,
                "reliability workflows must declare their token permissions explicitly",
            )
        )
        return violations
    for scope, value in sorted(declared.items()):
        allowed = maximum.get(scope)
        if allowed is None:
            violations.append(
                PolicyViolation(
                    "permissions-exceed-policy",
                    f"{location}.{scope}",
                    f"permission scope {scope!r} is not allowed by policy",
                )
            )
            continue
        actual_rank = _PERMISSION_RANK.get(value)
        allowed_rank = _PERMISSION_RANK.get(allowed)
        if actual_rank is None or allowed_rank is None or actual_rank > allowed_rank:
            violations.append(
                PolicyViolation(
                    "permissions-exceed-policy",
                    f"{location}.{scope}",
                    f"permission {scope}:{value} exceeds policy maximum {allowed}",
                )
            )
    for required_scope, allowed in sorted(maximum.items()):
        if required_scope not in declared:
            violations.append(
                PolicyViolation(
                    "permissions-missing",
                    f"{location}.{required_scope}",
                    f"required explicit permission {required_scope}:{allowed} is missing",
                )
            )
    return violations


def _is_external_action_pinned(uses: str) -> bool:
    if not uses or uses.startswith("./"):
        return True
    if uses.startswith("docker://"):
        return bool(_DOCKER_DIGEST_RE.fullmatch(uses))
    return bool(_SHA_ACTION_RE.fullmatch(uses))


def _checkout_steps(contract: WorkflowContract) -> list[tuple[str, WorkflowStep]]:
    rows: list[tuple[str, WorkflowStep]] = []
    for job_id, job in contract.jobs.items():
        for step in job.steps:
            if step.uses.startswith("actions/checkout@"):
                rows.append((job_id, step))
    return rows


def _artifact_steps(contract: WorkflowContract) -> list[tuple[str, WorkflowStep]]:
    rows: list[tuple[str, WorkflowStep]] = []
    for job_id, job in contract.jobs.items():
        for step in job.steps:
            if step.uses.startswith("actions/upload-artifact@"):
                rows.append((job_id, step))
    return rows


def _common_violations(contract: WorkflowContract, policy: ReliabilityPolicy) -> list[PolicyViolation]:
    violations: list[PolicyViolation] = []
    violations.extend(
        _permission_violations(contract.permissions, policy.max_permissions, location="permissions")
    )

    for job_id, job in sorted(contract.jobs.items()):
        if job.permissions:
            violations.extend(
                _permission_violations(
                    job.permissions,
                    policy.max_permissions,
                    location=f"jobs.{job_id}.permissions",
                )
            )
        for index, step in enumerate(job.steps):
            if step.uses and not _is_external_action_pinned(step.uses):
                violations.append(
                    PolicyViolation(
                        "action-not-sha-pinned",
                        f"jobs.{job_id}.steps[{index}].uses",
                        "external actions must use immutable commit SHA or image digest pins",
                    )
                )

    for job_id, step in _checkout_steps(contract):
        if step.with_values.get("persist-credentials") is not False:
            violations.append(
                PolicyViolation(
                    "checkout-persists-credentials",
                    f"jobs.{job_id}.checkout.persist-credentials",
                    "checkout must explicitly set persist-credentials to false",
                )
            )

    diagnostics = policy.raw.get("diagnostics")
    retention_days = diagnostics.get("retention_days") if isinstance(diagnostics, Mapping) else None
    for job_id, step in _artifact_steps(contract):
        condition = step.if_condition or ""
        if "always()" not in condition:
            violations.append(
                PolicyViolation(
                    "artifact-missing-always",
                    f"jobs.{job_id}.artifact.if",
                    "diagnostic artifact uploads must remain outcome-resilient with always()",
                )
            )
        actual_retention = step.with_values.get("retention-days")
        if actual_retention != retention_days:
            violations.append(
                PolicyViolation(
                    "artifact-retention",
                    f"jobs.{job_id}.artifact.retention-days",
                    f"artifact retention {actual_retention!r} does not match policy {retention_days!r}",
                )
            )
    return violations


def _deep_violations(contract: WorkflowContract, policy: ReliabilityPolicy) -> list[PolicyViolation]:
    violations: list[PolicyViolation] = []
    required_triggers = {"pull_request", "push", "workflow_dispatch"}
    missing_triggers = sorted(required_triggers - set(contract.triggers))
    for trigger in missing_triggers:
        violations.append(
            PolicyViolation(
                "missing-trigger",
                f"on.{trigger}",
                f"deep workflow must declare {trigger}",
            )
        )

    required_surfaces = set(policy.trigger_surfaces)
    for trigger_name in ("pull_request", "push"):
        trigger = contract.triggers.get(trigger_name)
        if trigger is None:
            continue
        for surface in sorted(required_surfaces - set(trigger.paths)):
            violations.append(
                PolicyViolation(
                    "missing-trigger-surface",
                    f"on.{trigger_name}.paths",
                    f"policy trigger surface {surface!r} is missing",
                )
            )
    push = contract.triggers.get("push")
    if push is not None and "main" not in push.branches:
        violations.append(
            PolicyViolation(
                "missing-main-branch",
                "on.push.branches",
                "deep workflow push trigger must include main",
            )
        )

    deep_gate = policy.raw.get("deep_gate")
    maximum_timeout = deep_gate.get("job_timeout_minutes") if isinstance(deep_gate, Mapping) else None
    for job_id, job in sorted(contract.jobs.items()):
        timeout = job.timeout_minutes
        if not isinstance(maximum_timeout, int) or isinstance(maximum_timeout, bool):
            violations.append(
                PolicyViolation("job-timeout", f"jobs.{job_id}.timeout-minutes", "policy timeout is invalid")
            )
            continue
        if timeout is None or timeout < 1 or timeout > maximum_timeout:
            violations.append(
                PolicyViolation(
                    "job-timeout",
                    f"jobs.{job_id}.timeout-minutes",
                    f"job timeout {timeout!r} must be between 1 and policy maximum {maximum_timeout}",
                )
            )
    if not contract.jobs:
        violations.append(PolicyViolation("jobs-missing", "jobs", "deep workflow must contain at least one job"))
    return violations


def verify_workflow_against_policy(
    contract: WorkflowContract,
    policy: ReliabilityPolicy,
    *,
    role: str,
) -> list[PolicyViolation]:
    """Return stable, machine-readable structural policy violations."""

    violations = _common_violations(contract, policy)
    if role == "deep":
        violations.extend(_deep_violations(contract, policy))
    else:
        violations.append(
            PolicyViolation("unsupported-workflow-role", "role", f"workflow role {role!r} is not supported yet")
        )
    return sorted(set(violations))


def _parse_workflow_argument(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("workflow must use ROLE=PATH")
    role, raw_path = value.split("=", 1)
    if not role or not raw_path:
        raise argparse.ArgumentTypeError("workflow must use non-empty ROLE=PATH")
    return role, Path(raw_path)


def _targets_from_args(values: Sequence[tuple[str, Path]] | None) -> dict[str, Path]:
    if not values:
        return dict(_DEFAULT_WORKFLOWS)
    targets: dict[str, Path] = {}
    for role, path in values:
        if role in targets:
            raise ValueError(f"duplicate workflow role: {role}")
        targets[role] = path
    return targets


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify GitHub Actions reliability workflows against policy.")
    parser.add_argument("--policy", type=Path, default=Path("reliability-policy.json"))
    parser.add_argument(
        "--workflow",
        action="append",
        type=_parse_workflow_argument,
        help="workflow target in ROLE=PATH form; defaults to the current deep gate",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    violations: list[PolicyViolation] = []
    try:
        policy = load_policy(args.policy)
        targets = _targets_from_args(args.workflow)
        for role, path in sorted(targets.items()):
            try:
                contract = read_workflow_contract(path)
            except Exception as exc:
                violations.append(
                    PolicyViolation(
                        "workflow-parse",
                        f"workflow.{role}",
                        f"{type(exc).__name__}: workflow contract could not be parsed",
                    )
                )
                continue
            violations.extend(verify_workflow_against_policy(contract, policy, role=role))
    except Exception as exc:
        violations.append(
            PolicyViolation("policy-load", "policy", f"{type(exc).__name__}: policy could not be loaded")
        )

    violations = sorted(set(violations))
    payload = {
        "status": "passed" if not violations else "failed",
        "violations": [item.to_dict() for item in violations],
    }
    print(json.dumps(payload, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
