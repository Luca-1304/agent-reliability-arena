from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..evaluator import evaluate_case
from ..models import Case
from .models import LiveRunConfig
from .reporting import verify_live_manifest


def replay_live_run(input_dir: Path) -> dict[str, Any]:
    """Verify and re-evaluate retained artifacts without network or tool execution."""
    input_dir = Path(input_dir)
    verify_live_manifest(input_dir)
    config = LiveRunConfig.from_dict(
        json.loads((input_dir / "config.json").read_text(encoding="utf-8"))
    )
    case = Case.from_dict(
        json.loads((input_dir / "case.json").read_text(encoding="utf-8"))
    )
    evaluation = evaluate_case(case)
    stored_evaluation = json.loads(
        (input_dir / "evaluation.json").read_text(encoding="utf-8")
    )
    if evaluation.to_dict() != stored_evaluation:
        raise ValueError("Replayed evaluation does not match the retained evaluation.")
    observation = json.loads(
        (input_dir / "observation.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (input_dir / "manifest.json").read_text(encoding="utf-8")
    )
    if manifest.get("config_digest") != config.digest:
        raise ValueError("Retained configuration digest does not match the manifest.")
    return {
        "run_id": config.run_id,
        "model": config.model,
        "manifest_verified": True,
        "status": evaluation.status.value,
        "completion_claimed": case.completion_claimed,
        "matches_contract": bool(observation.get("matches_contract")),
        "replayed_without_network": True,
        "replayed_without_tool_execution": True,
    }
