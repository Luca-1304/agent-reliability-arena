from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


_SCHEMA_VERSION = "git-operations-policy-v1"
_WORKFLOW_DIRECTORY = ".github/workflows"
_TOP_LEVEL_KEYS = {
    "schema_version",
    "workflow_directory",
    "default_permissions",
    "denied_triggers",
    "untrusted_run_expression_prefixes",
    "workflows",
    "external_settings",
}
_WORKFLOW_KEYS = {"write_jobs"}
_WRITE_JOB_KEYS = {"permissions", "authority_if", "allowed_mutations"}
_PERMISSION_VALUES = {"read", "write"}
_REQUIRED_DENIED_TRIGGERS = {
    "pull_request_target",
    "repository_dispatch",
    "workflow_run",
}
_REQUIRED_UNTRUSTED_PREFIXES = {
    "github.event.pull_request.title",
    "github.event.pull_request.body",
    "github.event.pull_request.head.ref",
    "github.event.pull_request.head.label",
    "github.event.issue.title",
    "github.event.issue.body",
    "github.event.comment.body",
    "github.event.review.body",
    "github.event.review_comment.body",
    "github.head_ref",
    "github.ref_name",
}
_ALLOWED_MUTATIONS = {"gh-release-create"}
_EXTERNAL_SETTING_STATES = {"externally_required_unverified"}


class GitOperationsPolicyError(ValueError):
    """Raised when the Git operations policy is malformed or over-broad."""


@dataclass(frozen=True)
class WriteJobPolicy:
    permissions: Mapping[str, str]
    authority_if: str | None
    allowed_mutations: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowOperationsPolicy:
    write_jobs: Mapping[str, WriteJobPolicy]


@dataclass(frozen=True)
class GitOperationsPolicy:
    schema_version: str
    workflow_directory: str
    default_permissions: Mapping[str, str]
    denied_triggers: tuple[str, ...]
    untrusted_run_expression_prefixes: tuple[str, ...]
    workflows: Mapping[str, WorkflowOperationsPolicy]
    external_settings: Mapping[str, str]


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GitOperationsPolicyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], *, location: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise GitOperationsPolicyError(
            f"{location} keys must be exact; missing={missing!r} unknown={unknown!r}"
        )


def _require_string_list(value: Any, *, location: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise GitOperationsPolicyError(f"{location} must be a non-empty list of strings")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise GitOperationsPolicyError(f"{location} must contain non-empty strings")
        if item in result:
            raise GitOperationsPolicyError(f"{location} contains duplicate value {item!r}")
        result.append(item)
    return tuple(result)


def _validate_permissions(value: Any, *, location: str) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise GitOperationsPolicyError(f"{location} must be a non-empty permission map")
    result: dict[str, str] = {}
    for scope, permission in value.items():
        if not isinstance(scope, str) or not scope:
            raise GitOperationsPolicyError(f"{location} contains an invalid permission scope")
        if permission not in _PERMISSION_VALUES:
            raise GitOperationsPolicyError(
                f"{location}.{scope} must be one of {sorted(_PERMISSION_VALUES)!r}"
            )
        result[scope] = permission
    return result


def _validate_workflow_name(name: Any) -> str:
    if not isinstance(name, str) or not name:
        raise GitOperationsPolicyError("workflow names must be non-empty strings")
    path = Path(name)
    if path.name != name or name in {".", ".."} or path.suffix not in {".yml", ".yaml"}:
        raise GitOperationsPolicyError(
            f"workflow name must be a basename ending in .yml or .yaml: {name!r}"
        )
    return name


def _parse_write_job(value: Any, *, location: str) -> WriteJobPolicy:
    if not isinstance(value, dict):
        raise GitOperationsPolicyError(f"{location} must be an object")
    _require_exact_keys(value, _WRITE_JOB_KEYS, location=location)
    permissions = _validate_permissions(value["permissions"], location=f"{location}.permissions")
    if "write" not in permissions.values():
        raise GitOperationsPolicyError(f"{location} must contain at least one write permission")

    authority_if = value["authority_if"]
    if authority_if is not None and (not isinstance(authority_if, str) or not authority_if.strip()):
        raise GitOperationsPolicyError(f"{location}.authority_if must be null or a non-empty string")

    raw_mutations = value["allowed_mutations"]
    if not isinstance(raw_mutations, list):
        raise GitOperationsPolicyError(f"{location}.allowed_mutations must be a list")
    mutations: list[str] = []
    for mutation in raw_mutations:
        if mutation not in _ALLOWED_MUTATIONS:
            raise GitOperationsPolicyError(
                f"{location}.allowed_mutations contains unsupported capability {mutation!r}"
            )
        if mutation in mutations:
            raise GitOperationsPolicyError(
                f"{location}.allowed_mutations contains duplicate capability {mutation!r}"
            )
        mutations.append(mutation)

    return WriteJobPolicy(
        permissions=dict(sorted(permissions.items())),
        authority_if=authority_if,
        allowed_mutations=tuple(mutations),
    )


def _parse_workflow(value: Any, *, location: str) -> WorkflowOperationsPolicy:
    if not isinstance(value, dict):
        raise GitOperationsPolicyError(f"{location} must be an object")
    _require_exact_keys(value, _WORKFLOW_KEYS, location=location)
    raw_write_jobs = value["write_jobs"]
    if not isinstance(raw_write_jobs, dict):
        raise GitOperationsPolicyError(f"{location}.write_jobs must be an object")
    write_jobs: dict[str, WriteJobPolicy] = {}
    for job_name, job_value in raw_write_jobs.items():
        if not isinstance(job_name, str) or not job_name:
            raise GitOperationsPolicyError(f"{location}.write_jobs contains an invalid job name")
        write_jobs[job_name] = _parse_write_job(
            job_value,
            location=f"{location}.write_jobs.{job_name}",
        )
    return WorkflowOperationsPolicy(write_jobs=dict(sorted(write_jobs.items())))


def load_git_operations_policy(path: Path) -> GitOperationsPolicy:
    """Load the closed repository Git-operations authority contract."""

    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            raw = json.load(handle, object_pairs_hook=_object_without_duplicates)
    except GitOperationsPolicyError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise GitOperationsPolicyError(f"could not load Git operations policy: {type(exc).__name__}") from exc

    if not isinstance(raw, dict):
        raise GitOperationsPolicyError("policy root must be an object")
    _require_exact_keys(raw, _TOP_LEVEL_KEYS, location="policy")

    if raw["schema_version"] != _SCHEMA_VERSION:
        raise GitOperationsPolicyError(f"schema_version must be {_SCHEMA_VERSION!r}")
    if raw["workflow_directory"] != _WORKFLOW_DIRECTORY:
        raise GitOperationsPolicyError(f"workflow_directory must be {_WORKFLOW_DIRECTORY!r}")

    default_permissions = _validate_permissions(
        raw["default_permissions"],
        location="default_permissions",
    )
    if default_permissions != {"contents": "read"}:
        raise GitOperationsPolicyError("default_permissions must be exactly contents:read")

    denied_triggers = _require_string_list(raw["denied_triggers"], location="denied_triggers")
    if set(denied_triggers) != _REQUIRED_DENIED_TRIGGERS:
        raise GitOperationsPolicyError(
            f"denied_triggers must be exactly {sorted(_REQUIRED_DENIED_TRIGGERS)!r}"
        )

    untrusted_prefixes = _require_string_list(
        raw["untrusted_run_expression_prefixes"],
        location="untrusted_run_expression_prefixes",
    )
    if set(untrusted_prefixes) != _REQUIRED_UNTRUSTED_PREFIXES:
        raise GitOperationsPolicyError(
            "untrusted_run_expression_prefixes must preserve the reviewed event-text boundary"
        )

    raw_workflows = raw["workflows"]
    if not isinstance(raw_workflows, dict) or not raw_workflows:
        raise GitOperationsPolicyError("workflows must be a non-empty object")
    workflows: dict[str, WorkflowOperationsPolicy] = {}
    for raw_name, workflow_value in raw_workflows.items():
        name = _validate_workflow_name(raw_name)
        workflows[name] = _parse_workflow(workflow_value, location=f"workflows.{name}")

    raw_external = raw["external_settings"]
    if not isinstance(raw_external, dict) or not raw_external:
        raise GitOperationsPolicyError("external_settings must be a non-empty object")
    external_settings: dict[str, str] = {}
    for setting, state in raw_external.items():
        if not isinstance(setting, str) or not setting:
            raise GitOperationsPolicyError("external_settings contains an invalid setting name")
        if state not in _EXTERNAL_SETTING_STATES:
            raise GitOperationsPolicyError(
                f"external_settings.{setting} has unsupported evidence state {state!r}"
            )
        external_settings[setting] = state

    return GitOperationsPolicy(
        schema_version=_SCHEMA_VERSION,
        workflow_directory=_WORKFLOW_DIRECTORY,
        default_permissions=dict(sorted(default_permissions.items())),
        denied_triggers=tuple(sorted(denied_triggers)),
        untrusted_run_expression_prefixes=tuple(sorted(untrusted_prefixes)),
        workflows=dict(sorted(workflows.items())),
        external_settings=dict(sorted(external_settings.items())),
    )
