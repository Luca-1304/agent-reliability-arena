from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.live_requests import PromptCatalog
from agent_reliability_arena.pilot_policy import PilotPolicy, build_pilot_preflight
from agent_reliability_arena.private_pilot import run_private_paired_pilot
from agent_reliability_arena.transports import OpenAIResponsesTransport


OPERATOR_CONFIRMATION = "I_APPROVE_ONE_PRIVATE_PILOT"


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(args: argparse.Namespace) -> dict[str, object]:
    if not args.approve_external_execution or args.operator_confirmation != OPERATOR_CONFIRMATION:
        raise RuntimeError(
            "Explicit operator approval is required: pass --approve-external-execution and the exact "
            f"--operator-confirmation value {OPERATOR_CONFIRMATION}."
        )
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        raise RuntimeError("Private provider execution is always refused inside GitHub Actions.")

    config = ExperimentConfig.from_dict(_read_json(args.config))
    catalog = PromptCatalog.from_dict(_read_json(args.catalog))
    policy = PilotPolicy.from_dict(_read_json(args.policy))
    if policy.provider != "openai-responses":
        raise RuntimeError("The local OpenAI pilot script requires provider 'openai-responses'.")
    if args.reviewed_policy_digest != policy.digest:
        raise RuntimeError("The reviewed policy digest does not match the exact policy file.")
    if not policy.external_execution_enabled:
        raise RuntimeError("External execution is disabled by the reviewed pilot policy.")

    preflight = build_pilot_preflight(config, catalog, policy)
    if preflight["policy_digest"] != args.reviewed_policy_digest:
        raise RuntimeError("The preflight policy digest does not match the reviewed digest.")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not isinstance(api_key, str) or not api_key.strip():
        raise RuntimeError("OPENAI_API_KEY must be supplied through the local process environment.")

    transport = OpenAIResponsesTransport(
        api_key=api_key,
        external_execution_approved=True,
    )
    summary = run_private_paired_pilot(
        config,
        catalog,
        policy,
        transport,
        args.output,
        reviewed_policy_digest=args.reviewed_policy_digest,
        external_execution_approved=True,
    )
    return {
        "status": summary["status"],
        "private_output": str(args.output),
        "scenario_id": summary["scenario_id"],
        "provider": summary["provider"],
        "model_id": summary["model_id"],
        "model_version": summary["model_version"],
        "calls_started": summary["gate"]["calls_started"],
        "observed_total_tokens": summary["gate"]["observed_total_tokens"],
        "ledger_records": summary["ledger"]["records"],
        "ledger_sha256": summary["ledger"]["ledger_sha256"],
        "comparative_claim_permitted": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one local private paired pilot. This command can make paid provider requests and "
            "is never run by the test or release workflow."
        )
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviewed-policy-digest", required=True)
    parser.add_argument("--approve-external-execution", action="store_true")
    parser.add_argument("--operator-confirmation", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = _run(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
