from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import ExperimentConfig
from .experiment import execute_fixture_experiment
from .live_requests import PromptCatalog
from .pilot_policy import PilotPolicy, build_pilot_preflight
from .public_export import write_public_export
from .replay import replay_experiment


def _load_config(path: Path) -> ExperimentConfig:
    return ExperimentConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _load_catalog(path: Path) -> PromptCatalog:
    return PromptCatalog.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _load_pilot_policy(path: Path) -> PilotPolicy:
    return PilotPolicy.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))


def _guard(function) -> int:
    try:
        _print(function())
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2


def run_main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic Agent Reliability Arena fixture experiment.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(_guard(lambda: execute_fixture_experiment(_load_config(args.config), args.output)))


def replay_main() -> None:
    parser = argparse.ArgumentParser(description="Verify and replay an Arena artifact directory without execution.")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(_guard(lambda: replay_experiment(args.input)))


def export_web_main() -> None:
    parser = argparse.ArgumentParser(description="Export a reduced, read-only Arena web data bundle.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(_guard(lambda: write_public_export(args.input, args.output)))


def preflight_pilot_main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and print a provider-free pilot permission and budget manifest."
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(
        _guard(
            lambda: build_pilot_preflight(
                _load_config(args.config),
                _load_catalog(args.catalog),
                _load_pilot_policy(args.policy),
            )
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agent Reliability Arena commands.")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    replay = sub.add_parser("replay")
    replay.add_argument("--input", type=Path, required=True)
    export = sub.add_parser("export-web")
    export.add_argument("--input", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    preflight = sub.add_parser("preflight-pilot")
    preflight.add_argument("--config", type=Path, required=True)
    preflight.add_argument("--catalog", type=Path, required=True)
    preflight.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "run":
        return _guard(lambda: execute_fixture_experiment(_load_config(args.config), args.output))
    if args.command == "replay":
        return _guard(lambda: replay_experiment(args.input))
    if args.command == "export-web":
        return _guard(lambda: write_public_export(args.input, args.output))
    return _guard(
        lambda: build_pilot_preflight(
            _load_config(args.config),
            _load_catalog(args.catalog),
            _load_pilot_policy(args.policy),
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
