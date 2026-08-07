from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


_REQUIRED_ROLES = ("fast", "deep", "specialist")
_ADVISORY_ROLES = ("scheduled",)
_ALLOWED_ROLES = frozenset(_REQUIRED_ROLES + _ADVISORY_ROLES)
_FINAL_STATUSES = frozenset({"passed", "failed", "blocked", "unknown", "pending"})
_MINIMUM_PRIOR_SAMPLES = 10


@dataclass(frozen=True)
class ReliabilitySummary:
    decision: str
    blocking_roles: tuple[str, ...]
    advisory_roles: tuple[str, ...]
    missing_required_roles: tuple[str, ...]
    duplicate_roles: tuple[str, ...]
    input_errors: tuple[str, ...]
    timings: dict[str, int | float | None]
    observations: tuple[str, ...]
    records: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "layered-reliability-summary-v1",
            "decision": self.decision,
            "blocking_roles": list(self.blocking_roles),
            "advisory_roles": list(self.advisory_roles),
            "missing_required_roles": list(self.missing_required_roles),
            "duplicate_roles": list(self.duplicate_roles),
            "input_errors": list(self.input_errors),
            "timings": dict(self.timings),
            "observations": list(self.observations),
            "records": [dict(record) for record in self.records],
            "authoritative": False,
        }

    def to_markdown(self) -> str:
        lines = [
            "## Layered reliability summary",
            "",
            f"**Decision:** `{self.decision}`",
            "",
            "> This is a human-readable aggregation. The underlying machine records remain authoritative.",
            "",
            "| Role | Required | Status |",
            "| --- | --- | --- |",
        ]
        by_role = {str(record.get("role")): record for record in self.records}
        for role in _REQUIRED_ROLES + _ADVISORY_ROLES:
            record = by_role.get(role)
            status = str(record.get("status")) if record else "missing"
            required = "yes" if role in _REQUIRED_ROLES else "no"
            lines.append(f"| {role} | {required} | {status} |")
        lines.extend(["", "### Observational timing", ""])
        for key in (
            "command_samples",
            "median_command_seconds",
            "max_command_seconds",
            "pass_samples",
            "median_pass_seconds",
            "max_pass_seconds",
            "total_seconds",
        ):
            lines.append(f"- `{key}`: {self.timings.get(key)}")
        if self.observations:
            lines.extend(["", "### Observations", ""])
            lines.extend(f"- {item}" for item in self.observations)
        if self.input_errors:
            lines.extend(["", "### Input errors", ""])
            lines.extend(f"- {item}" for item in self.input_errors)
        return "\n".join(lines) + "\n"


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if result < 0:
        return None
    return result


def _durations(records: Sequence[Mapping[str, object]]) -> tuple[list[float], list[float], list[float]]:
    command_durations: list[float] = []
    pass_durations: list[float] = []
    totals: list[float] = []
    for record in records:
        commands = record.get("commands")
        if isinstance(commands, list):
            for command in commands:
                if isinstance(command, Mapping):
                    value = _number(command.get("duration_seconds"))
                    if value is not None:
                        command_durations.append(value)
        passes = record.get("passes")
        if isinstance(passes, list):
            for pass_row in passes:
                if isinstance(pass_row, Mapping):
                    value = _number(pass_row.get("duration_seconds"))
                    if value is not None:
                        pass_durations.append(value)
        timings = record.get("timings")
        if isinstance(timings, Mapping):
            value = _number(timings.get("total_seconds"))
            if value is not None:
                totals.append(value)
        direct_total = _number(record.get("total_seconds"))
        if direct_total is not None:
            totals.append(direct_total)
    return command_durations, pass_durations, totals


def _timing_stats(records: Sequence[Mapping[str, object]]) -> dict[str, int | float | None]:
    commands, passes, totals = _durations(records)
    return {
        "command_samples": len(commands),
        "median_command_seconds": float(statistics.median(commands)) if commands else None,
        "max_command_seconds": max(commands) if commands else None,
        "pass_samples": len(passes),
        "median_pass_seconds": float(statistics.median(passes)) if passes else None,
        "max_pass_seconds": max(passes) if passes else None,
        "total_seconds": sum(totals) if totals else None,
    }


def _prior_total_seconds(sample: Mapping[str, object]) -> float | None:
    direct = _number(sample.get("total_seconds"))
    if direct is not None:
        return direct
    timings = sample.get("timings")
    if isinstance(timings, Mapping):
        return _number(timings.get("total_seconds"))
    return None


def _normalize_records(
    records: Sequence[Mapping[str, object]],
) -> tuple[list[dict[str, object]], list[str], set[str]]:
    normalized: list[dict[str, object]] = []
    errors: list[str] = []
    seen: set[str] = set()
    duplicates: set[str] = set()
    for index, record in enumerate(records):
        role_raw = record.get("role")
        role = role_raw.strip().lower() if isinstance(role_raw, str) else ""
        if not role:
            errors.append(f"record[{index}] missing non-empty role")
            continue
        if role not in _ALLOWED_ROLES:
            errors.append(f"record[{index}] uses unsupported role {role!r}")
            continue
        if role in seen:
            duplicates.add(role)
        seen.add(role)

        status_raw = record.get("status", record.get("final_status"))
        status = status_raw.strip().lower() if isinstance(status_raw, str) else "unknown"
        if status not in _FINAL_STATUSES:
            errors.append(f"record[{index}] role {role!r} has unsupported status {status!r}")
            status = "unknown"

        expected_required = role in _REQUIRED_ROLES
        required_raw = record.get("required", expected_required)
        if not isinstance(required_raw, bool):
            errors.append(f"record[{index}] role {role!r} required must be boolean")
        elif required_raw is not expected_required:
            errors.append(
                f"record[{index}] role {role!r} required={required_raw} contradicts role contract"
            )

        row = dict(record)
        row["role"] = role
        row["status"] = status
        row["required"] = expected_required
        normalized.append(row)
    return normalized, errors, duplicates


def summarize(
    records: Sequence[Mapping[str, object]],
    *,
    prior_samples: Sequence[Mapping[str, object]] = (),
    input_errors: Sequence[str] = (),
    minimum_prior_samples: int = _MINIMUM_PRIOR_SAMPLES,
) -> ReliabilitySummary:
    if minimum_prior_samples < _MINIMUM_PRIOR_SAMPLES:
        raise ValueError(
            f"minimum_prior_samples must be at least {_MINIMUM_PRIOR_SAMPLES} to avoid false thresholds"
        )
    normalized, normalization_errors, duplicates = _normalize_records(records)
    errors = tuple(input_errors) + tuple(normalization_errors)
    by_role: dict[str, dict[str, object]] = {}
    for record in normalized:
        role = str(record["role"])
        by_role.setdefault(role, record)

    missing = tuple(sorted(role for role in _REQUIRED_ROLES if role not in by_role))
    blocking = tuple(
        sorted(
            role
            for role in _REQUIRED_ROLES
            if role in by_role and str(by_role[role].get("status")) != "passed"
        )
    )
    advisory = tuple(
        sorted(
            role
            for role in _ADVISORY_ROLES
            if role in by_role and str(by_role[role].get("status")) != "passed"
        )
    )

    if errors or missing or duplicates or blocking:
        decision = "blocked"
    elif advisory:
        decision = "verified-with-advisory"
    else:
        decision = "verified"

    timings = _timing_stats(normalized)
    observations: list[str] = []
    prior_totals = [
        value
        for sample in prior_samples
        if (value := _prior_total_seconds(sample)) is not None
    ]
    current_total = timings.get("total_seconds")
    if (
        isinstance(current_total, (int, float))
        and not isinstance(current_total, bool)
        and len(prior_totals) >= minimum_prior_samples
    ):
        recent_median = float(statistics.median(prior_totals))
        if float(current_total) > recent_median:
            observations.append("slower-than-recent-median")
        timings["prior_sample_count"] = len(prior_totals)
        timings["recent_median_total_seconds"] = recent_median
    else:
        timings["prior_sample_count"] = len(prior_totals)
        timings["recent_median_total_seconds"] = None

    return ReliabilitySummary(
        decision=decision,
        blocking_roles=blocking,
        advisory_roles=advisory,
        missing_required_roles=missing,
        duplicate_roles=tuple(sorted(duplicates)),
        input_errors=errors,
        timings=timings,
        observations=tuple(observations),
        records=tuple(normalized),
    )


def _load_json_object(path: Path) -> tuple[dict[str, object] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"missing manifest: {path}"
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON manifest {path}: {type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, f"manifest must be a JSON object: {path}"
    return payload, None


def summarize_files(
    paths: Sequence[Path],
    *,
    prior_paths: Sequence[Path] = (),
    minimum_prior_samples: int = _MINIMUM_PRIOR_SAMPLES,
) -> ReliabilitySummary:
    records: list[dict[str, object]] = []
    prior: list[dict[str, object]] = []
    errors: list[str] = []
    for path in paths:
        payload, error = _load_json_object(path)
        if error:
            errors.append(error)
        elif payload is not None:
            records.append(payload)
    for path in prior_paths:
        payload, error = _load_json_object(path)
        if error:
            errors.append(error)
        elif payload is not None:
            prior.append(payload)
    return summarize(
        records,
        prior_samples=prior,
        input_errors=errors,
        minimum_prior_samples=minimum_prior_samples,
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a non-authoritative human summary from layered reliability machine records."
    )
    parser.add_argument("--manifest", action="append", type=Path, required=True)
    parser.add_argument("--prior-sample", action="append", type=Path, default=[])
    parser.add_argument("--minimum-prior-samples", type=int, default=_MINIMUM_PRIOR_SAMPLES)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    result = summarize_files(
        args.manifest,
        prior_paths=args.prior_sample,
        minimum_prior_samples=args.minimum_prior_samples,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(result.to_markdown(), encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": result.decision,
                "blocking_roles": list(result.blocking_roles),
                "advisory_roles": list(result.advisory_roles),
                "observations": list(result.observations),
            },
            sort_keys=True,
        )
    )
    return 1 if result.decision == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
