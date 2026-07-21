from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifacts import verify_manifest


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_public_export(input_dir: Path) -> dict[str, Any]:
    verify_manifest(input_dir)
    config = _load(input_dir / "config.json")
    metrics = _load(input_dir / "aggregate_metrics.json")
    scenarios = []
    for scenario_id in sorted(config["scenarios"]):
        general = _load(input_dir / "runs" / "general" / f"{scenario_id}.json")
        specialist = _load(input_dir / "runs" / "specialist" / f"{scenario_id}.json")
        scenarios.append(
            {
                "scenario_id": scenario_id,
                "general": {
                    "status": general["final_status"],
                    "completion_claimed": general["completion_claimed"],
                    "false_completion": general["false_completion"],
                    "logical_model_calls": general["logical_model_calls"],
                    "attempts": general["attempts"],
                },
                "specialist": {
                    "status": specialist["final_status"],
                    "completion_claimed": specialist["completion_claimed"],
                    "false_completion": specialist["false_completion"],
                    "recovered": specialist["recovered"],
                    "logical_model_calls": specialist["logical_model_calls"],
                    "strategy": specialist["strategy"],
                    "audit_records": specialist["audit_records"],
                    "recovery": specialist["recovery"],
                    "synthesis": specialist["synthesis"],
                    "attempts": specialist["attempts"],
                },
            }
        )
    return {
        "schema_version": "1",
        "title": "Agent Reliability Arena",
        "tagline": "Same model. Same tools. Same evidence rules. Different orchestration.",
        "evidence_status": metrics["evidence_status"],
        "claims_boundary": metrics["claims_boundary"],
        "experiment": {
            "experiment_id": config["experiment_id"],
            "model_id": config["model_id"],
            "model_version": config["model_version"],
            "prompt_version": config["prompt_version"],
            "seed": config["seed"],
            "contract": config["contract"],
            "config_digest": _load(input_dir / "runs" / "general" / f"{config['scenarios'][0]}.json")["config_digest"],
        },
        "metrics": metrics,
        "scenarios": scenarios,
    }


def write_public_export(input_dir: Path, output: Path) -> dict[str, Any]:
    payload = build_public_export(input_dir)
    if output.exists() and output.is_dir():
        raise IsADirectoryError(f"Public export path is a directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "output": str(output),
        "evidence_status": payload["evidence_status"],
        "scenarios": len(payload["scenarios"]),
    }
