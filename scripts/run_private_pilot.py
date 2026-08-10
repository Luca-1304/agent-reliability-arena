from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.live_requests import PromptCatalog
from agent_reliability_arena.pilot_policy import PilotPolicy, build_pilot_preflight
from agent_reliability_arena.private_pilot import run_private_paired_pilot
from agent_reliability_arena.stage7_candidate import (
    read_stage7_json_object,
    verify_stage7_candidate,
    verify_stage7_execution_policy,
    verify_stage7_privacy_gate,
)
from agent_reliability_arena.transports import OpenAIResponsesTransport


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = ROOT / "examples" / "stage7_candidate"
PRIVACY_GATE = CANDIDATE_ROOT / "privacy-execution-gate.json"
OPERATOR_CONFIRMATION = "I_APPROVE_ONE_PRIVATE_PILOT"


def _verify_prepared_private_output(path: Path) -> Path:
    target = Path(path)
    if target.is_symlink():
        raise RuntimeError("Private pilot output directory must not be a symlink.")
    if not target.exists():
        raise RuntimeError(
            "Private pilot output directory must already exist before credential lookup."
        )
    if not target.is_dir():
        raise RuntimeError("Private pilot output path must be a directory.")
    if any(target.iterdir()):
        raise RuntimeError("Private pilot output directory must be empty before credential lookup.")
    if os.name != "nt":
        mode = stat.S_IMODE(target.stat().st_mode)
        if mode & 0o777 != 0o700:
            raise RuntimeError(
                "Private pilot output directory must have operator-only mode 0700 before credential lookup."
            )
    return target


def _run(args: argparse.Namespace) -> dict[str, object]:
    if not args.approve_external_execution or args.operator_confirmation != OPERATOR_CONFIRMATION:
        raise RuntimeError(
            "Explicit operator approval is required: pass --approve-external-execution and the exact "
            f"--operator-confirmation value {OPERATOR_CONFIRMATION}."
        )
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        raise RuntimeError("Private provider execution is always refused inside GitHub Actions.")

    privacy_gate = verify_stage7_privacy_gate(PRIVACY_GATE)
    if not privacy_gate["execution_permitted"]:
        raise RuntimeError(
            "Stage 7 privacy execution gate is still open; real-provider execution remains blocked."
        )

    candidate = verify_stage7_candidate(CANDIDATE_ROOT, args.catalog)
    execution = verify_stage7_execution_policy(
        CANDIDATE_ROOT,
        args.config,
        args.catalog,
        args.policy,
    )
    if execution["candidate_packet_digest"] != candidate["packet_digest"]:
        raise RuntimeError("Stage 7 execution policy is not bound to the verified candidate packet.")
    if args.reviewed_policy_digest != execution["policy_digest"]:
        raise RuntimeError("The reviewed policy digest does not match the exact enabled Stage 7 policy.")

    config = ExperimentConfig.from_dict(
        read_stage7_json_object(args.config, "Stage 7 execution config")
    )
    catalog = PromptCatalog.from_dict(
        read_stage7_json_object(args.catalog, "Stage 7 prompt catalogue")
    )
    policy = PilotPolicy.from_dict(
        read_stage7_json_object(args.policy, "Stage 7 enabled policy")
    )
    if policy.provider != "openai-responses":
        raise RuntimeError("The local OpenAI pilot script requires provider 'openai-responses'.")
    if not policy.external_execution_enabled:
        raise RuntimeError("External execution is disabled by the reviewed pilot policy.")

    preflight = build_pilot_preflight(config, catalog, policy)
    if preflight["policy_digest"] != args.reviewed_policy_digest:
        raise RuntimeError("The preflight policy digest does not match the reviewed digest.")
    if preflight["manifest_digest"] != execution["preflight_manifest_digest"]:
        raise RuntimeError("The execution preflight no longer matches the reviewed Stage 7 boundary.")

    output = _verify_prepared_private_output(args.output)

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
        output,
        reviewed_policy_digest=args.reviewed_policy_digest,
        external_execution_approved=True,
    )
    return {
        "status": summary["status"],
        "private_output": str(output),
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
            "Run the reviewed Stage 7 local private paired pilot. This command can make paid "
            "provider requests only after the source-controlled privacy gate is closed."
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
