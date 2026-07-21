from __future__ import annotations

import json
from pathlib import Path

from .artifacts import verify_manifest


def replay_experiment(output: Path) -> dict[str, object]:
    verify_manifest(output)
    metrics = json.loads((output / "aggregate_metrics.json").read_text(encoding="utf-8"))
    paired_lines = [line for line in (output / "paired_results.jsonl").read_text(encoding="utf-8").splitlines() if line]
    return {
        "manifest_verified": True,
        "evidence_status": metrics["evidence_status"],
        "general_verified": metrics["conditions"]["general"]["verified_complete"],
        "specialist_verified": metrics["conditions"]["specialist"]["verified_complete"],
        "paired_runs": len(paired_lines),
        "false_completion_reduction": metrics["paired"]["false_completion_reduction"],
        "additional_logical_model_calls": metrics["paired"]["additional_logical_model_calls"],
    }
