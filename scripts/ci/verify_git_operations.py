from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

try:
    from scripts.ci.git_operations_policy import (
        GitOperationsPolicy,
        GitOperationsPolicyError,
        WorkflowOperationsPolicy,
        WriteJobPolicy,
        load_git_operations_policy,
    )
    from scripts.ci.workflow_contract import WorkflowContract, read_workflow_contract
except ModuleNotFoundError:  # Direct execution from scripts/ci.
    from git_operations_policy import (  # type: ignore[no-redef]
        GitOperationsPolicy,
        GitOperationsPolicyError,
        WorkflowOperationsPolicy,
        WriteJobPolicy,
        load_git_operations_policy,
    )
    from workflow_contract import WorkflowContract, read_workflow_contract  # type: ignore[no-redef]


_SHA_ACTION_RE = re.compile(r"^[^@\s]+@[0-9a-fA-F]{40}$")
_DOCKER_DIGEST_RE = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-fA-F]{64}$")
_GITHUB_EXPRESSION_RE = re.compile(r"\$\{\{\s*([^}]+?)\s*\}\}")
_MUTATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("git-push", re.compile(r"(?m)(?:^|[;&|]\s*|\n\s*)git\s+push\b")),
    ("git-update-ref", re.compile(r"(?m)(?:^|[;&|]\s*|\n\s*)git\s+update-ref\b")),
    ("git-tag", re.compile(r"(?m)(?:^|[;&|]\s*|\n\s*)git\s+tag\b")),
    ("gh-release-create", re.compile(r"(?m)(?:^|[;&|]\s*|\n\s*)gh\s+release\s+create\b")),
    ("gh-release-mutate", re.compile(r"(?m)(?:^|[;&|]\s*|\n\s*)gh\s+release\s+(?:delete|edit|upload)\b")),
    (
        "gh-api-mutate",
        re.compile(
            r"(?is)(?:^|[;&|]\s*|\n\s*)gh\s+api\b[^\n]*(?:(?:--method|-X)\s+(?:POST|PUT|PATCH|DELETE))"
        ),
    ),
)


@dataclass(frozen=True, order=True)
class GitOperationsViolation:
    code: str
    location: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "location": self.location, "message": self.message}


def _is_external_action_pinned(uses: str) -> bool:
    if not uses or uses.startswith("./"):
        return True
    if uses.startswith("docker://"):
        return bool(_DOCKER_DIGEST_RE.fullmatch(uses))
    return bool(_SHA_ACTION_RE.fullmatch(uses))


def _discover_workflows(root: Path, policy: GitOperationsPolicy) -> dict[str, Path]:
    workflow_root = root / policy.workflow_directory
    if not workflow_root.is_dir():
        return {}
    paths = [
        path
        for pattern in ("*.yml", "*.yaml")
        for path in workflow_root.glob(pattern)
        if path.is_file()
    ]
    return {path.name: path for path in sorted(paths, key=lambda item: item.name)}


def _write_permissions(permissions: Mapping[str, str]) -> dict[str, str]:
    return {scope: value for scope, value in permissions.items() if value == "write"}


def _mutation_capabilities(run: str) -> tuple[str, ...]:
    found = [name for name, pattern in _MUTATION_PATTERNS if pattern.search(run)]
    return tuple(sorted(set(found)))


def _expression_violations(
    run: str,
    *,
    prefixes: Iterable[str],
    location: str,
) -> list[GitOperationsViolation]:
    violations: list[GitOperationsViolation] = []
    prefix_tuple = tuple(prefixes)
    for match in _GITHUB_EXPRESSION_RE.finditer(run):
        expression = match.group(1).strip()
        if expression.startswith(prefix_tuple):
            violations.append(
                GitOperationsViolation(
                    "untrusted-expression-in-run",
                    location,
                    "untrusted GitHub event text must not be interpolated directly into shell source",
                )
            )
            break
    return violations


def _verify_action_and_checkout_steps(
    workflow_name: str,
    contract: WorkflowContract,
) -> list[GitOperationsViolation]:
    violations: list[GitOperationsViolation] = []
    for job_name, job in sorted(contract.jobs.items()):
        for index, step in enumerate(job.steps):
            location = f"{workflow_name}.jobs.{job_name}.steps[{index}]"
            if step.uses and not _is_external_action_pinned(step.uses):
                violations.append(
                    GitOperationsViolation(
                        "action-not-sha-pinned",
                        f"{location}.uses",
                        "external actions must use a full immutable commit SHA or image digest",
                    )
                )
            if step.uses.startswith("actions/checkout@"):
                if step.with_values.get("persist-credentials") is not False:
                    violations.append(
                        GitOperationsViolation(
                            "checkout-persists-credentials",
                            f"{location}.with.persist-credentials",
                            "checkout must explicitly set persist-credentials to false",
                        )
                    )
    return violations


def _verify_triggers(
    workflow_name: str,
    contract: WorkflowContract,
    policy: GitOperationsPolicy,
) -> list[GitOperationsViolation]:
    violations: list[GitOperationsViolation] = []
    for trigger in sorted(set(contract.triggers) & set(policy.denied_triggers)):
        violations.append(
            GitOperationsViolation(
                "dangerous-trigger",
                f"{workflow_name}.on.{trigger}",
                f"trigger {trigger!r} is denied by Git operations policy",
            )
        )
    return violations


def _verify_top_permissions(
    workflow_name: str,
    contract: WorkflowContract,
    policy: GitOperationsPolicy,
) -> list[GitOperationsViolation]:
    if dict(contract.permissions) == dict(policy.default_permissions):
        return []
    return [
        GitOperationsViolation(
            "permissions-default",
            f"{workflow_name}.permissions",
            f"top-level permissions must equal {dict(policy.default_permissions)!r}",
        )
    ]


def _verify_write_jobs(
    workflow_name: str,
    contract: WorkflowContract,
    workflow_policy: WorkflowOperationsPolicy,
) -> list[GitOperationsViolation]:
    violations: list[GitOperationsViolation] = []
    expected = workflow_policy.write_jobs

    for job_name, job in sorted(contract.jobs.items()):
        actual_permissions = dict(job.permissions)
        actual_writes = _write_permissions(actual_permissions)
        expected_job = expected.get(job_name)
        if actual_writes and expected_job is None:
            violations.append(
                GitOperationsViolation(
                    "write-job-not-allowed",
                    f"{workflow_name}.jobs.{job_name}.permissions",
                    "job requests write authority but is not allow-listed",
                )
            )
            continue
        if expected_job is None:
            continue
        if actual_permissions != dict(expected_job.permissions):
            violations.append(
                GitOperationsViolation(
                    "write-job-permissions",
                    f"{workflow_name}.jobs.{job_name}.permissions",
                    "job permission map does not exactly match its reviewed write-authority policy",
                )
            )
        if expected_job.authority_if is not None and job.if_condition != expected_job.authority_if:
            violations.append(
                GitOperationsViolation(
                    "write-authority-condition",
                    f"{workflow_name}.jobs.{job_name}.if",
                    "write-capable job does not use the exact reviewed event/ref authority condition",
                )
            )

    for job_name in sorted(set(expected) - set(contract.jobs)):
        violations.append(
            GitOperationsViolation(
                "write-job-missing",
                f"{workflow_name}.jobs.{job_name}",
                "policy grants write authority to a job that is not present in the workflow",
            )
        )
    return violations


def _verify_run_bodies(
    workflow_name: str,
    contract: WorkflowContract,
    workflow_policy: WorkflowOperationsPolicy,
    policy: GitOperationsPolicy,
) -> list[GitOperationsViolation]:
    violations: list[GitOperationsViolation] = []
    observed_by_job: dict[str, set[str]] = {name: set() for name in workflow_policy.write_jobs}

    for job_name, job in sorted(contract.jobs.items()):
        expected_job: WriteJobPolicy | None = workflow_policy.write_jobs.get(job_name)
        allowed = set(expected_job.allowed_mutations) if expected_job is not None else set()
        for index, step in enumerate(job.steps):
            if not step.run:
                continue
            location = f"{workflow_name}.jobs.{job_name}.steps[{index}].run"
            violations.extend(
                _expression_violations(
                    step.run,
                    prefixes=policy.untrusted_run_expression_prefixes,
                    location=location,
                )
            )
            for capability in _mutation_capabilities(step.run):
                if expected_job is not None:
                    observed_by_job[job_name].add(capability)
                if capability not in allowed:
                    violations.append(
                        GitOperationsViolation(
                            "remote-mutation-not-allowed",
                            location,
                            f"remote mutation capability {capability!r} is not allow-listed for this job",
                        )
                    )

    for job_name, expected_job in sorted(workflow_policy.write_jobs.items()):
        missing = set(expected_job.allowed_mutations) - observed_by_job.get(job_name, set())
        for capability in sorted(missing):
            violations.append(
                GitOperationsViolation(
                    "allowed-mutation-not-observed",
                    f"{workflow_name}.jobs.{job_name}",
                    f"policy grants mutation capability {capability!r} but the reviewed command is absent",
                )
            )
    return violations


def verify_repository(
    root: Path,
    policy: GitOperationsPolicy,
) -> list[GitOperationsViolation]:
    """Return stable violations for repository-wide Git/GitHub operation authority."""

    root = Path(root).resolve()
    violations: list[GitOperationsViolation] = []
    discovered = _discover_workflows(root, policy)
    policy_names = set(policy.workflows)
    discovered_names = set(discovered)

    for name in sorted(discovered_names - policy_names):
        violations.append(
            GitOperationsViolation(
                "workflow-unclassified",
                f"{policy.workflow_directory}/{name}",
                "workflow exists but has no Git operations policy classification",
            )
        )
    for name in sorted(policy_names - discovered_names):
        violations.append(
            GitOperationsViolation(
                "workflow-missing",
                f"{policy.workflow_directory}/{name}",
                "policy classifies a workflow that is not present",
            )
        )

    for workflow_name in sorted(discovered_names & policy_names):
        path = discovered[workflow_name]
        try:
            contract = read_workflow_contract(path)
        except Exception as exc:
            violations.append(
                GitOperationsViolation(
                    "workflow-parse",
                    f"{policy.workflow_directory}/{workflow_name}",
                    f"{type(exc).__name__}: workflow could not be parsed fail-closed",
                )
            )
            continue
        workflow_policy = policy.workflows[workflow_name]
        violations.extend(_verify_top_permissions(workflow_name, contract, policy))
        violations.extend(_verify_triggers(workflow_name, contract, policy))
        violations.extend(_verify_action_and_checkout_steps(workflow_name, contract))
        violations.extend(_verify_write_jobs(workflow_name, contract, workflow_policy))
        violations.extend(_verify_run_bodies(workflow_name, contract, workflow_policy, policy))

    return sorted(set(violations))


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify repository Git/GitHub operation authority.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--policy", type=Path, default=Path("git-operations-policy.json"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        policy = load_git_operations_policy(args.policy)
        violations = verify_repository(args.root, policy)
    except (GitOperationsPolicyError, OSError, ValueError) as exc:
        violations = [
            GitOperationsViolation(
                "policy-load",
                "policy",
                f"{type(exc).__name__}: Git operations policy could not be verified",
            )
        ]

    payload = {
        "status": "passed" if not violations else "failed",
        "violations": [item.to_dict() for item in violations],
    }
    print(json.dumps(payload, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
