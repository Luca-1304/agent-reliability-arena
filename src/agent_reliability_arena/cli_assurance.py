from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from .assurance_router import AssuranceReport, classify_paths


DEFAULT_POLICY_NAME = "reliability-policy.json"


class AssuranceInputError(ValueError):
    """Raised for expected CLI input or local Git acquisition failures."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise AssuranceInputError(message)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = _ArgumentParser(
        description=(
            "Route changed repository paths to non-authoritative assurance evidence."
        )
    )
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--paths-file", type=Path)
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _load_policy(path: Path) -> tuple[str, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssuranceInputError(f"policy file is unavailable: {path}") from exc
    except OSError as exc:
        raise AssuranceInputError(f"policy file cannot be read: {path}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssuranceInputError(f"policy file is not valid UTF-8 JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise AssuranceInputError("policy must be a JSON object")
    triggers = payload.get("trigger_surfaces")
    if not isinstance(triggers, list) or not all(
        isinstance(item, str) and item.strip() for item in triggers
    ):
        raise AssuranceInputError(
            "policy trigger_surfaces must be a list of non-empty strings"
        )
    return tuple(triggers)


def _read_paths_file(path: Path) -> tuple[str, ...]:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise AssuranceInputError(f"paths file is unavailable or unreadable: {path}") from exc
    return tuple(line.strip() for line in content.splitlines() if line.strip())


def _git_paths(base: str, head: str) -> tuple[str, ...]:
    git = shutil.which("git")
    if git is None:
        raise AssuranceInputError("git executable is unavailable")
    completed = subprocess.run(
        [git, "diff", "--name-only", "--no-renames", base, head, "--"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        if detail:
            first_line = detail.splitlines()[0]
            raise AssuranceInputError(f"git diff failed: {first_line}")
        raise AssuranceInputError("git diff failed")
    return tuple(line.strip() for line in completed.stdout.splitlines() if line.strip())


def _input_paths(args: argparse.Namespace) -> tuple[str, ...]:
    has_paths = bool(args.path)
    has_file = args.paths_file is not None
    has_git = args.base is not None or args.head is not None

    if has_git and (args.base is None or args.head is None):
        raise AssuranceInputError("--base and --head must be provided together")

    mode_count = int(has_paths) + int(has_file) + int(has_git)
    if mode_count != 1:
        raise AssuranceInputError(
            "exactly one input mode is required: --path, --paths-file, or --base/--head"
        )

    if has_paths:
        return tuple(args.path)
    if has_file:
        return _read_paths_file(args.paths_file)
    return _git_paths(args.base, args.head)


def _human_output(report: AssuranceReport) -> str:
    surfaces = ", ".join(report.touched_surfaces) or "none"
    attention = "yes" if report.attention_required else "no"
    lines = [
        "Assurance Router (non-authoritative)",
        f"Attention required: {attention}",
        f"Surfaces: {surfaces}",
        "Evidence:",
    ]
    if report.evidence_ids:
        lines.extend(f"- {item}" for item in report.evidence_ids)
    else:
        lines.append("- none")
    if report.unknown_paths:
        lines.append("Unknown paths:")
        lines.extend(f"- {path}" for path in report.unknown_paths)
    if report.outside_reliability_trigger_surface:
        lines.append("Outside reliability trigger surface:")
        lines.extend(
            f"- {path}" for path in report.outside_reliability_trigger_surface
        )
    if report.observations:
        lines.append("Observations:")
        lines.extend(f"- {item}" for item in report.observations)
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
        paths = _input_paths(args)
        policy_path = args.policy if args.policy is not None else Path.cwd() / DEFAULT_POLICY_NAME
        triggers = _load_policy(policy_path)
        report = classify_paths(paths, triggers)
    except (AssuranceInputError, ValueError) as exc:
        print(f"assurance-router: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(report.to_json(), end="")
    else:
        print(_human_output(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
