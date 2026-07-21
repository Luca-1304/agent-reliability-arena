from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .config import ExperimentConfig
from .metrics import aggregate_metrics, pair_runs
from .models import ArenaRun


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(payload))


def _write_jsonl(path: Path, rows: Iterable[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def _ensure_empty_directory(path: Path) -> None:
    if path.exists():
        if not path.is_dir() or any(path.iterdir()):
            raise FileExistsError("Artifact output directory must be empty.")
    else:
        path.mkdir(parents=True)


def _report(config: ExperimentConfig, metrics: dict[str, Any]) -> str:
    general = metrics["conditions"]["general"]
    specialist = metrics["conditions"]["specialist"]
    paired = metrics["paired"]
    return f"""# Agent Reliability Arena — Deterministic Fixture Results

**Evidence status:** deterministic fixture; these are software-validation results, not external-model performance.

## Controlled comparison

- Experiment: `{config.experiment_id}`
- Fixture model label: `{config.model_id}` version `{config.model_version}`
- Scenarios: {len(config.scenarios)}
- Same contract digest: `{config.contract.digest}`
- Maximum mutation attempts: {config.max_mutation_attempts}

## Results

| Metric | General | Specialist |
|---|---:|---:|
| Verified completion | {general['verified_complete']}/{general['total_runs']} | {specialist['verified_complete']}/{specialist['total_runs']} |
| False completion | {general['false_completion']} | {specialist['false_completion']} |
| Claim precision | {general['claim_precision']:.2f} | {specialist['claim_precision']:.2f} |
| Recovered scenarios | {general['recovered']} | {specialist['recovered']} |
| Logical role calls | {general['logical_model_calls']} | {specialist['logical_model_calls']} |

The specialist fixture improves {paired['verified_completion_gain']} paired outcomes and removes {paired['false_completion_reduction']} false-completion cases, while using {paired['additional_logical_model_calls']} additional logical role calls.

## Claims boundary

No token, latency, price, or external-model score is fabricated. Real-model conclusions require fixed model versions, repeated paired runs, measured usage, and uncertainty analysis.
"""


def _manifest_payload(output: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item.name != "manifest.json"):
        rows.append(
            {
                "path": path.relative_to(output).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
            }
        )
    return {"schema_version": "1", "files": rows}


def verify_manifest(output: Path) -> bool:
    manifest_path = output / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("Manifest is missing.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {row["path"]: row for row in manifest.get("files", [])}
    actual_paths = {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    if actual_paths != set(expected):
        extra = sorted(actual_paths - set(expected))
        missing = sorted(set(expected) - actual_paths)
        if extra:
            raise ValueError("Manifest has unlisted files: " + ", ".join(extra))
        raise ValueError("Manifest references missing files: " + ", ".join(missing))
    for relative, row in expected.items():
        path = output / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != row["sha256"]:
            raise ValueError(f"Artifact digest mismatch: {relative}")
        if path.stat().st_size != row["size"]:
            raise ValueError(f"Artifact size mismatch: {relative}")
    return True


def write_experiment_artifacts(
    config: ExperimentConfig,
    runs: Iterable[ArenaRun],
    output: Path,
) -> dict[str, Any]:
    _ensure_empty_directory(output)
    run_list = sorted(list(runs), key=lambda run: (run.condition, run.scenario_id))
    general = [run for run in run_list if run.condition == "general"]
    specialist = [run for run in run_list if run.condition == "specialist"]
    pairs = pair_runs(general, specialist)
    metrics = aggregate_metrics(run_list)
    _write_json(output / "config.json", config.to_dict())
    for run in run_list:
        _write_json(output / "runs" / run.condition / f"{run.scenario_id}.json", run.to_dict())
    _write_jsonl(output / "paired_results.jsonl", pairs)
    _write_json(output / "aggregate_metrics.json", metrics)
    (output / "report.md").write_text(_report(config, metrics), encoding="utf-8")
    _write_json(output / "manifest.json", _manifest_payload(output))
    return {
        "output": str(output),
        "total_runs": len(run_list),
        "paired_runs": len(pairs),
        "manifest_verified": verify_manifest(output),
        "evidence_status": metrics["evidence_status"],
    }
