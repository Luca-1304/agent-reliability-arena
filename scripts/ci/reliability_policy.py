from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class PolicyError(ValueError):
    """Raised when the reliability policy is missing, malformed, or weakened."""


_SUPPORTED_PYTHON = ("3.10", "3.11", "3.12", "3.13")
_DEEP_PYTHON = ("3.10", "3.13")
_DETERMINISM_CLASSES = ("byte", "semantic", "bounded")
_CACHE_MODES = ("warm", "cold")
_INSTALL_MODES = ("editable", "wheel", "clean-room-wheel")
_FAILURE_CATEGORIES = (
    "TEST",
    "BUILD",
    "PACKAGE",
    "REPLAY",
    "DETERMINISM",
    "SECURITY",
    "DEPENDENCY",
    "ENVIRONMENT",
    "TIMEOUT",
    "CONCURRENCY",
    "POLICY",
    "UNKNOWN",
)
_REQUIRED_DIAGNOSTIC_FILES = ("manifest.json", "summary.json", "summary.md", "events.jsonl")
_REQUIRED_SCHEDULED_DIMENSIONS = (
    "latest-compatible-build-tools",
    "cold-cache",
    "dependency-resolution",
)
_REQUIRED_TRIGGER_SURFACES = {
    "src/**",
    "tests/**",
    "scripts/**",
    "examples/**",
    "security/**",
    "release/**",
    "reference_runs/**",
    "web/**",
    "docs/**",
    "citation/**",
    "requirements/**",
    "schemas/**",
    "reliability-policy.json",
    "pyproject.toml",
    "README.md",
    "CHANGELOG.md",
    "ROADMAP.md",
    ".github/workflows/**",
}
_TOP_LEVEL_KEYS = {
    "schema_version",
    "supported_python",
    "deep_gate",
    "permissions",
    "install_modes",
    "cache_modes",
    "determinism_classes",
    "diagnostics",
    "trigger_surfaces",
    "scheduled",
}
_DEEP_GATE_KEYS = {
    "python",
    "minimum_passes",
    "timezone",
    "locale",
    "hash_seeds",
    "command_timeout_seconds",
    "pass_timeout_seconds",
    "job_timeout_minutes",
}
_PERMISSION_KEYS = {"maximum", "persist_credentials"}
_DIAGNOSTIC_KEYS = {
    "schema_version",
    "retention_days",
    "required_files",
    "failure_categories",
}
_SCHEDULED_KEYS = {"blocking_by_default", "dimensions"}


@dataclass(frozen=True)
class ReliabilityPolicy:
    schema_version: str
    supported_python: tuple[str, ...]
    deep_python: tuple[str, ...]
    stress_passes: int
    max_permissions: dict[str, str]
    persist_credentials: bool
    determinism_classes: tuple[str, ...]
    cache_modes: tuple[str, ...]
    trigger_surfaces: tuple[str, ...]
    raw: dict[str, object]


def _require_mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PolicyError(f"{field} must be an object")
    return value


def _require_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise PolicyError(f"{field} must be an array")
    return value


def _require_bool(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise PolicyError(f"{field} must be a boolean")
    return value


def _require_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PolicyError(f"{field} must be an integer")
    return value


def _require_positive_int(value: object, *, field: str) -> int:
    result = _require_int(value, field=field)
    if result < 1:
        raise PolicyError(f"{field} must be positive")
    return result


def _require_string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise PolicyError(f"{field} must be a non-empty string")
    return value


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    rows = _require_list(value, field=field)
    result: list[str] = []
    for index, row in enumerate(rows):
        result.append(_require_string(row, field=f"{field}[{index}]"))
    if len(set(result)) != len(result):
        raise PolicyError(f"{field} must not contain duplicates")
    return tuple(result)


def _reject_unknown(mapping: Mapping[str, object], allowed: set[str], *, field: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        prefix = "unknown policy keys" if field == "policy" else f"unknown {field} keys"
        raise PolicyError(f"{prefix}: {unknown}")
    missing = sorted(allowed - set(mapping))
    if missing:
        raise PolicyError(f"missing {field} keys: {missing}")


def validate_policy_payload(payload: Mapping[str, object]) -> None:
    policy = _require_mapping(payload, field="policy")
    _reject_unknown(policy, _TOP_LEVEL_KEYS, field="policy")

    if _require_string(policy["schema_version"], field="schema_version") != "reliability-policy-v1":
        raise PolicyError("schema_version must be reliability-policy-v1")

    supported_python = _string_tuple(policy["supported_python"], field="supported_python")
    if supported_python != _SUPPORTED_PYTHON:
        raise PolicyError(f"supported_python must be exactly {_SUPPORTED_PYTHON}")

    deep_gate = _require_mapping(policy["deep_gate"], field="deep_gate")
    _reject_unknown(deep_gate, _DEEP_GATE_KEYS, field="deep_gate")
    deep_python = _string_tuple(deep_gate["python"], field="deep_gate.python")
    if deep_python != _DEEP_PYTHON:
        raise PolicyError(f"deep_gate.python must be exactly {_DEEP_PYTHON}")
    if not set(deep_python).issubset(supported_python):
        raise PolicyError("deep_gate.python must be a subset of supported_python")

    minimum_passes = _require_int(deep_gate["minimum_passes"], field="deep_gate.minimum_passes")
    if minimum_passes < 15:
        raise PolicyError("deep_gate.minimum_passes must be at least 15")

    if _require_string(deep_gate["timezone"], field="deep_gate.timezone") != "UTC":
        raise PolicyError("deep_gate.timezone must be UTC")
    if _require_string(deep_gate["locale"], field="deep_gate.locale") != "C.UTF-8":
        raise PolicyError("deep_gate.locale must be C.UTF-8")

    hash_seeds_raw = _require_list(deep_gate["hash_seeds"], field="deep_gate.hash_seeds")
    hash_seeds = tuple(_require_int(seed, field="deep_gate.hash_seeds[]") for seed in hash_seeds_raw)
    if len(set(hash_seeds)) != len(hash_seeds):
        raise PolicyError("deep_gate.hash_seeds must not contain duplicates")
    if len(hash_seeds) < minimum_passes:
        raise PolicyError("deep_gate.hash_seeds must provide at least one unique seed per minimum pass")
    if any(seed < 0 for seed in hash_seeds):
        raise PolicyError("deep_gate.hash_seeds must be non-negative")

    command_timeout = _require_positive_int(
        deep_gate["command_timeout_seconds"], field="deep_gate.command_timeout_seconds"
    )
    pass_timeout = _require_positive_int(
        deep_gate["pass_timeout_seconds"], field="deep_gate.pass_timeout_seconds"
    )
    job_timeout = _require_positive_int(
        deep_gate["job_timeout_minutes"], field="deep_gate.job_timeout_minutes"
    )
    if command_timeout > pass_timeout:
        raise PolicyError("deep_gate.command_timeout_seconds must not exceed pass_timeout_seconds")
    if pass_timeout > job_timeout * 60:
        raise PolicyError("deep_gate.pass_timeout_seconds must not exceed job timeout")
    if job_timeout > 180:
        raise PolicyError("deep_gate.job_timeout_minutes must not exceed 180")

    permissions = _require_mapping(policy["permissions"], field="permissions")
    _reject_unknown(permissions, _PERMISSION_KEYS, field="permissions")
    maximum = _require_mapping(permissions["maximum"], field="permissions.maximum")
    normalized_permissions = {
        _require_string(key, field="permissions.maximum key"): _require_string(
            value, field=f"permissions.maximum.{key}"
        )
        for key, value in maximum.items()
    }
    if normalized_permissions != {"contents": "read"}:
        raise PolicyError("permissions.maximum must be exactly {'contents': 'read'}")
    if _require_bool(permissions["persist_credentials"], field="permissions.persist_credentials"):
        raise PolicyError("permissions.persist_credentials must be false")

    install_modes = _string_tuple(policy["install_modes"], field="install_modes")
    if install_modes != _INSTALL_MODES:
        raise PolicyError(f"install_modes must be exactly {_INSTALL_MODES}")

    cache_modes = _string_tuple(policy["cache_modes"], field="cache_modes")
    if cache_modes != _CACHE_MODES:
        raise PolicyError(f"cache_modes must be exactly {_CACHE_MODES}")

    determinism_classes = _string_tuple(policy["determinism_classes"], field="determinism_classes")
    if determinism_classes != _DETERMINISM_CLASSES:
        raise PolicyError(f"determinism_classes must be exactly {_DETERMINISM_CLASSES}")

    diagnostics = _require_mapping(policy["diagnostics"], field="diagnostics")
    _reject_unknown(diagnostics, _DIAGNOSTIC_KEYS, field="diagnostics")
    if _require_string(diagnostics["schema_version"], field="diagnostics.schema_version") != "reliability-evidence-v1":
        raise PolicyError("diagnostics.schema_version must be reliability-evidence-v1")
    retention_days = _require_int(diagnostics["retention_days"], field="diagnostics.retention_days")
    if not 1 <= retention_days <= 30:
        raise PolicyError("diagnostics.retention_days must be between 1 and 30")
    required_files = _string_tuple(diagnostics["required_files"], field="diagnostics.required_files")
    if required_files != _REQUIRED_DIAGNOSTIC_FILES:
        raise PolicyError(f"diagnostics.required_files must be exactly {_REQUIRED_DIAGNOSTIC_FILES}")
    failure_categories = _string_tuple(
        diagnostics["failure_categories"], field="diagnostics.failure_categories"
    )
    if failure_categories != _FAILURE_CATEGORIES:
        raise PolicyError(f"diagnostics.failure_categories must be exactly {_FAILURE_CATEGORIES}")

    trigger_surfaces = _string_tuple(policy["trigger_surfaces"], field="trigger_surfaces")
    missing_surfaces = sorted(_REQUIRED_TRIGGER_SURFACES - set(trigger_surfaces))
    if missing_surfaces:
        raise PolicyError(f"trigger_surfaces missing required entries: {missing_surfaces}")

    scheduled = _require_mapping(policy["scheduled"], field="scheduled")
    _reject_unknown(scheduled, _SCHEDULED_KEYS, field="scheduled")
    if _require_bool(scheduled["blocking_by_default"], field="scheduled.blocking_by_default"):
        raise PolicyError("scheduled.blocking_by_default must be false")
    scheduled_dimensions = _string_tuple(scheduled["dimensions"], field="scheduled.dimensions")
    if scheduled_dimensions != _REQUIRED_SCHEDULED_DIMENSIONS:
        raise PolicyError(f"scheduled.dimensions must be exactly {_REQUIRED_SCHEDULED_DIMENSIONS}")


def load_policy(path: Path) -> ReliabilityPolicy:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PolicyError(f"policy file is missing: {path}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PolicyError(f"policy file is not valid UTF-8 JSON: {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise PolicyError("policy must be a JSON object")
    validate_policy_payload(payload)
    deep_gate = _require_mapping(payload["deep_gate"], field="deep_gate")
    permissions = _require_mapping(payload["permissions"], field="permissions")
    return ReliabilityPolicy(
        schema_version=str(payload["schema_version"]),
        supported_python=tuple(str(value) for value in _require_list(payload["supported_python"], field="supported_python")),
        deep_python=tuple(str(value) for value in _require_list(deep_gate["python"], field="deep_gate.python")),
        stress_passes=int(deep_gate["minimum_passes"]),
        max_permissions={str(key): str(value) for key, value in _require_mapping(permissions["maximum"], field="permissions.maximum").items()},
        persist_credentials=bool(permissions["persist_credentials"]),
        determinism_classes=tuple(str(value) for value in _require_list(payload["determinism_classes"], field="determinism_classes")),
        cache_modes=tuple(str(value) for value in _require_list(payload["cache_modes"], field="cache_modes")),
        trigger_surfaces=tuple(str(value) for value in _require_list(payload["trigger_surfaces"], field="trigger_surfaces")),
        raw=dict(payload),
    )
