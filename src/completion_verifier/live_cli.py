from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from .live import (
    FakeResponsesTransport,
    LiveRunConfig,
    LiveResponsesRunner,
    OpenAIResponsesTransport,
    ResponseRecord,
    ResponseRequest,
    replay_live_run,
    verify_live_manifest,
    write_live_run_artifacts,
)


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path}:{exc.lineno}:{exc.colno}: invalid JSON: {exc.msg}"
        ) from exc


def load_config(path: Path, model: str | None = None) -> LiveRunConfig:
    config = LiveRunConfig.from_dict(_load_json(path))
    return config.with_model(model) if model is not None else config


def load_fixtures(path: Path) -> list[ResponseRecord]:
    raw = _load_json(path)
    if isinstance(raw, dict):
        raw = raw.get("responses")
    if not isinstance(raw, list) or not raw:
        raise ValueError("Fake fixture must contain a non-empty response list.")
    return [ResponseRecord.from_dict(item) for item in raw]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run or replay a narrowly confined Responses-style file-write task "
            "whose final status is independently observed."
        )
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    fake = subparsers.add_parser("fake", help="Run deterministic offline fixtures.")
    fake.add_argument("--config", type=Path, required=True)
    fake.add_argument("--fixture", type=Path, required=True)
    fake.add_argument("--output", type=Path, required=True)
    fake.add_argument("--dry-run", action="store_true")

    openai = subparsers.add_parser(
        "openai", help="Run one explicitly confirmed live OpenAI Responses session."
    )
    openai.add_argument("--config", type=Path, required=True)
    openai.add_argument("--output", type=Path, required=True)
    openai.add_argument("--model", required=True)
    openai.add_argument("--confirm-live", action="store_true")
    openai.add_argument("--dry-run", action="store_true")

    replay = subparsers.add_parser(
        "replay", help="Verify and re-evaluate retained artifacts without a call."
    )
    replay.add_argument("--input", type=Path, required=True)
    return parser


def _preview(config: LiveRunConfig) -> dict[str, object]:
    return {
        "run_id": config.run_id,
        "provider": config.provider,
        "model": config.model,
        "config_digest": config.digest,
        "contract_digest": config.contract.digest,
        "maximum_api_requests": config.max_tool_rounds + 1,
        "request_preview": ResponseRequest.first(config).to_dict(),
        "live_call_performed": False,
        "price_estimated": False,
    }


def _run(config: LiveRunConfig, transport, output: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="acv-live-sandbox-") as directory:
        result = LiveResponsesRunner().run(config, transport, Path(directory))
    write_live_run_artifacts(result, output)
    verify_live_manifest(output)
    return {
        **result.to_dict(),
        "output_dir": str(output),
        "manifest_verified": True,
        "maximum_api_requests": config.max_tool_rounds + 1,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.mode == "replay":
            payload = replay_live_run(args.input)
        elif args.mode == "fake":
            config = load_config(args.config)
            if args.dry_run:
                payload = _preview(config) | {
                    "fixture": str(args.fixture),
                    "mode": "fake",
                }
            else:
                payload = _run(
                    config,
                    FakeResponsesTransport(load_fixtures(args.fixture)),
                    args.output,
                )
        else:
            config = load_config(args.config, args.model)
            if args.dry_run:
                payload = _preview(config) | {"mode": "openai"}
            else:
                if not args.confirm_live:
                    raise ValueError(
                        "Live OpenAI execution requires explicit --confirm-live."
                    )
                if not os.environ.get("OPENAI_API_KEY", "").strip():
                    raise ValueError(
                        "Live OpenAI execution requires OPENAI_API_KEY in the environment."
                    )
                payload = _run(config, OpenAIResponsesTransport(), args.output)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
