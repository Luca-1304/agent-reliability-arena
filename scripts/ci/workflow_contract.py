from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeAlias


Scalar: TypeAlias = str | int | bool | None


@dataclass(frozen=True)
class TriggerContract:
    name: str
    paths: tuple[str, ...] = ()
    branches: tuple[str, ...] = ()
    crons: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowStep:
    name: str | None = None
    step_id: str | None = None
    uses: str = ""
    if_condition: str | None = None
    with_values: dict[str, Scalar] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowJob:
    job_id: str
    name: str | None = None
    runs_on: str | None = None
    timeout_minutes: int | None = None
    permissions: dict[str, str] = field(default_factory=dict)
    steps: tuple[WorkflowStep, ...] = ()


@dataclass(frozen=True)
class WorkflowContract:
    source: str
    triggers: dict[str, TriggerContract]
    permissions: dict[str, str]
    concurrency: dict[str, Scalar]
    jobs: dict[str, WorkflowJob]


def _strip_comment(value: str) -> str:
    single = False
    double = False
    for index, character in enumerate(value):
        if character == "'" and not double:
            single = not single
        elif character == '"' and not single:
            double = not double
        elif character == "#" and not single and not double:
            if index == 0 or value[index - 1].isspace():
                return value[:index].rstrip()
    return value.rstrip()


def _split_mapping(value: str) -> tuple[str, str] | None:
    single = False
    double = False
    for index, character in enumerate(value):
        if character == "'" and not double:
            single = not single
        elif character == '"' and not single:
            double = not double
        elif character == ":" and not single and not double:
            return value[:index].strip(), value[index + 1 :].strip()
    return None


def _parse_scalar(value: str) -> Scalar:
    value = _strip_comment(value).strip()
    if not value:
        return None
    if value.startswith("${{") or "${{" in value:
        return value
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
        return parsed if isinstance(parsed, str) else value
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "~"}:
        return None
    if re.fullmatch(r"-?[0-9]+", value):
        return int(value)
    return value


def _parse_inline_list(value: str) -> tuple[str, ...]:
    value = _strip_comment(value).strip()
    if not (value.startswith("[") and value.endswith("]")):
        scalar = _parse_scalar(value)
        return () if scalar is None else (str(scalar),)
    body = value[1:-1].strip()
    if not body:
        return ()
    items: list[str] = []
    start = 0
    single = False
    double = False
    for index, character in enumerate(body):
        if character == "'" and not double:
            single = not single
        elif character == '"' and not single:
            double = not double
        elif character == "," and not single and not double:
            scalar = _parse_scalar(body[start:index])
            if scalar is not None:
                items.append(str(scalar))
            start = index + 1
    scalar = _parse_scalar(body[start:])
    if scalar is not None:
        items.append(str(scalar))
    return tuple(items)


def _indent_and_content(raw: str, *, line_number: int) -> tuple[int, str]:
    prefix = raw[: len(raw) - len(raw.lstrip(" \t"))]
    if "\t" in prefix:
        raise ValueError(f"tab indentation is not supported at line {line_number}")
    return len(prefix), _strip_comment(raw[len(prefix) :]).rstrip()


def read_workflow_contract(path: Path) -> WorkflowContract:
    """Parse only the GitHub Actions fields that the reliability policy enforces.

    This is intentionally not a general YAML parser. It preserves GitHub's literal
    ``on`` key and raw ``${{ ... }}`` expressions while failing on ambiguous
    structural indentation that matters to the enforced contract.
    """

    text = path.read_text(encoding="utf-8")
    trigger_builders: dict[str, dict[str, list[str]]] = {}
    permissions: dict[str, str] = {}
    concurrency: dict[str, Scalar] = {}
    job_builders: dict[str, dict[str, object]] = {}

    section: str | None = None
    current_trigger: str | None = None
    current_trigger_list: str | None = None
    current_job: str | None = None
    job_subsection: str | None = None
    current_step: dict[str, object] | None = None
    in_step_with = False

    for line_number, raw in enumerate(text.splitlines(), start=1):
        indent, content = _indent_and_content(raw, line_number=line_number)
        if not content:
            continue

        if indent == 0:
            mapping = _split_mapping(content)
            if mapping is None:
                section = None
                continue
            key, _ = mapping
            section = key if key in {"on", "permissions", "concurrency", "jobs"} else None
            current_trigger = None
            current_trigger_list = None
            current_job = None
            job_subsection = None
            current_step = None
            in_step_with = False
            continue

        if section == "on":
            if indent == 2:
                mapping = _split_mapping(content)
                if mapping is None:
                    continue
                trigger_name, _ = mapping
                current_trigger = trigger_name
                current_trigger_list = None
                trigger_builders.setdefault(trigger_name, {"paths": [], "branches": [], "crons": []})
                continue
            if current_trigger is None:
                continue
            builder = trigger_builders[current_trigger]
            if indent == 4 and content.startswith("- "):
                item_mapping = _split_mapping(content[2:].strip())
                if item_mapping is not None and item_mapping[0] == "cron":
                    scalar = _parse_scalar(item_mapping[1])
                    if scalar is not None:
                        builder["crons"].append(str(scalar))
                continue
            if indent == 4:
                mapping = _split_mapping(content)
                if mapping is None:
                    continue
                key, raw_value = mapping
                if key in {"paths", "branches"}:
                    current_trigger_list = key
                    if raw_value:
                        builder[key].extend(_parse_inline_list(raw_value))
                        current_trigger_list = None
                else:
                    current_trigger_list = None
                continue
            if indent == 6 and current_trigger_list and content.startswith("- "):
                scalar = _parse_scalar(content[2:])
                if scalar is not None:
                    builder[current_trigger_list].append(str(scalar))
                continue

        if section == "permissions" and indent == 2:
            mapping = _split_mapping(content)
            if mapping is not None:
                key, raw_value = mapping
                scalar = _parse_scalar(raw_value)
                if scalar is not None:
                    permissions[key] = str(scalar)
            continue

        if section == "concurrency" and indent == 2:
            mapping = _split_mapping(content)
            if mapping is not None:
                key, raw_value = mapping
                concurrency[key] = _parse_scalar(raw_value)
            continue

        if section != "jobs":
            continue

        if indent == 2:
            mapping = _split_mapping(content)
            if mapping is None:
                continue
            current_job, _ = mapping
            job_builders.setdefault(
                current_job,
                {
                    "name": None,
                    "runs_on": None,
                    "timeout_minutes": None,
                    "permissions": {},
                    "steps": [],
                },
            )
            job_subsection = None
            current_step = None
            in_step_with = False
            continue

        if current_job is None:
            continue
        job = job_builders[current_job]

        if indent == 4:
            mapping = _split_mapping(content)
            if mapping is None:
                continue
            key, raw_value = mapping
            current_step = None
            in_step_with = False
            if key == "steps":
                job_subsection = "steps"
                continue
            if key == "permissions":
                job_subsection = "permissions"
                continue
            job_subsection = None
            scalar = _parse_scalar(raw_value)
            if key == "name":
                job["name"] = None if scalar is None else str(scalar)
            elif key == "runs-on":
                job["runs_on"] = None if scalar is None else str(scalar)
            elif key == "timeout-minutes":
                job["timeout_minutes"] = scalar if isinstance(scalar, int) and not isinstance(scalar, bool) else None
            continue

        if job_subsection == "permissions" and indent == 6 and not content.startswith("- "):
            mapping = _split_mapping(content)
            if mapping is not None:
                key, raw_value = mapping
                scalar = _parse_scalar(raw_value)
                if scalar is not None:
                    cast_permissions = job["permissions"]
                    assert isinstance(cast_permissions, dict)
                    cast_permissions[key] = str(scalar)
            continue

        if job_subsection != "steps":
            continue

        if indent == 6 and content.startswith("- "):
            current_step = {"name": None, "step_id": None, "uses": "", "if_condition": None, "with_values": {}}
            cast_steps = job["steps"]
            assert isinstance(cast_steps, list)
            cast_steps.append(current_step)
            in_step_with = False
            mapping = _split_mapping(content[2:].strip())
            if mapping is not None:
                key, raw_value = mapping
                scalar = _parse_scalar(raw_value)
                if key == "name":
                    current_step["name"] = None if scalar is None else str(scalar)
                elif key == "id":
                    current_step["step_id"] = None if scalar is None else str(scalar)
                elif key == "uses":
                    current_step["uses"] = "" if scalar is None else str(scalar)
                elif key == "if":
                    current_step["if_condition"] = None if scalar is None else str(scalar)
            continue

        if current_step is None:
            continue

        if indent == 8:
            mapping = _split_mapping(content)
            if mapping is None:
                continue
            key, raw_value = mapping
            if key == "with":
                in_step_with = True
                continue
            in_step_with = False
            scalar = _parse_scalar(raw_value)
            if key == "name":
                current_step["name"] = None if scalar is None else str(scalar)
            elif key == "id":
                current_step["step_id"] = None if scalar is None else str(scalar)
            elif key == "uses":
                current_step["uses"] = "" if scalar is None else str(scalar)
            elif key == "if":
                current_step["if_condition"] = None if scalar is None else str(scalar)
            continue

        if indent == 10 and in_step_with:
            mapping = _split_mapping(content)
            if mapping is not None:
                key, raw_value = mapping
                cast_with = current_step["with_values"]
                assert isinstance(cast_with, dict)
                cast_with[key] = _parse_scalar(raw_value)
            continue

    triggers = {
        name: TriggerContract(
            name=name,
            paths=tuple(values["paths"]),
            branches=tuple(values["branches"]),
            crons=tuple(values["crons"]),
        )
        for name, values in trigger_builders.items()
    }
    jobs: dict[str, WorkflowJob] = {}
    for job_id, values in job_builders.items():
        steps_raw = values["steps"]
        assert isinstance(steps_raw, list)
        steps = tuple(
            WorkflowStep(
                name=step["name"] if isinstance(step["name"], str) else None,
                step_id=step["step_id"] if isinstance(step["step_id"], str) else None,
                uses=step["uses"] if isinstance(step["uses"], str) else "",
                if_condition=step["if_condition"] if isinstance(step["if_condition"], str) else None,
                with_values=dict(step["with_values"]) if isinstance(step["with_values"], dict) else {},
            )
            for step in steps_raw
        )
        raw_job_permissions = values["permissions"]
        assert isinstance(raw_job_permissions, dict)
        jobs[job_id] = WorkflowJob(
            job_id=job_id,
            name=values["name"] if isinstance(values["name"], str) else None,
            runs_on=values["runs_on"] if isinstance(values["runs_on"], str) else None,
            timeout_minutes=(
                values["timeout_minutes"]
                if isinstance(values["timeout_minutes"], int) and not isinstance(values["timeout_minutes"], bool)
                else None
            ),
            permissions={str(key): str(value) for key, value in raw_job_permissions.items()},
            steps=steps,
        )

    return WorkflowContract(
        source=path.as_posix(),
        triggers=triggers,
        permissions=permissions,
        concurrency=concurrency,
        jobs=jobs,
    )
