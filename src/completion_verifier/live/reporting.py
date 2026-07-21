from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from ..sandbox.reporting import case_dict
from .models import LiveRunResult


def _json_text(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _jsonl_text(values: Iterable[object]) -> str:
    return "".join(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
        for value in values
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prepare_output(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Output directory is non-empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)


def _report(result: LiveRunResult) -> str:
    return f"""# Optional Responses sandbox run

Generated at: {result.config.generated_at}

This run used a narrow `write_file` tool inside a confined local sandbox. The final verifier status comes from independent local observation, not the model's completion claim or tool receipt.

## Configuration

- Run: `{result.config.run_id}`
- Provider: `{result.config.provider}`
- Requested model: `{result.config.model}`
- Prompt version: `{result.config.prompt_version}`
- Configuration digest: `{result.config.digest}`
- Maximum tool rounds: {result.config.max_tool_rounds}
- Maximum output tokens per request: {result.config.max_output_tokens}
- Store response state: `false`

## Result

- Verifier status: `{result.evaluation.status.value}`
- Model claimed completion: `{str(result.completion_claimed).lower()}`
- Independent postcondition matched: `{str(result.observation.matches_contract).lower()}`
- API requests: {len(result.requests)}
- Executed tool calls: {sum(item.executed for item in result.tool_outputs)}
- Recorded errors: {len(result.errors)}

## Trust boundary

Requests, responses, function calls, tool outputs, source reports, independent observations, canonical cases, evaluations, and usage remain separate artifacts. API keys, authorization headers, client configuration, and environment dumps are never intentionally persisted.

## Limitations

A successful local observation does not prove remote state, user authorization, causal attribution outside this process, or production-grade operating-system isolation. A single live run is not representative model-performance evidence.
"""


def write_live_run_artifacts(result: LiveRunResult, output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    _prepare_output(output_dir)
    files: dict[str, str] = {
        "config.json": _json_text(result.config.to_dict()),
        "requests.jsonl": _jsonl_text(request.to_dict() for request in result.requests),
        "responses.jsonl": _jsonl_text(response.to_dict() for response in result.responses),
        "function_calls.jsonl": _jsonl_text(call.to_dict() for call in result.function_calls),
        "tool_outputs.jsonl": _jsonl_text(item.to_dict() for item in result.tool_outputs),
        "source_report.json": _json_text(result.source_report.to_dict()),
        "observation.json": _json_text(result.observation.to_dict()),
        "case.json": _json_text(case_dict(result.case)),
        "evaluation.json": _json_text(result.evaluation.to_dict()),
        "usage.json": _json_text(result.usage),
        "errors.json": _json_text(list(result.errors)),
        "report.md": _report(result),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content, encoding="utf-8")

    manifest = {
        "schema_version": "1",
        "run_id": result.config.run_id,
        "config_digest": result.config.digest,
        "generated_at": result.config.generated_at,
        "transport": result.transport_name,
        "transport_version": result.transport_version,
        "files": {
            path.name: _sha256(path)
            for path in sorted(output_dir.iterdir())
            if path.is_file() and not path.is_symlink()
        },
    }
    (output_dir / "manifest.json").write_text(
        _json_text(manifest), encoding="utf-8"
    )
    verify_live_manifest(output_dir)
    return output_dir


def verify_live_manifest(output_dir: Path) -> bool:
    output_dir = Path(output_dir)
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("Live-run manifest is missing or unsafe.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("Live-run manifest files mapping is invalid.")
    actual_names = {
        path.name
        for path in output_dir.iterdir()
        if path.is_file() and not path.is_symlink() and path.name != "manifest.json"
    }
    listed_names = set(files)
    unlisted = sorted(actual_names - listed_names)
    if unlisted:
        raise ValueError("Live-run directory contains unlisted files: " + ", ".join(unlisted))
    missing = sorted(listed_names - actual_names)
    if missing:
        raise ValueError("Live-run manifest files are missing: " + ", ".join(missing))
    for relative, expected in files.items():
        path = output_dir / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Manifest file is missing or unsafe: {relative}")
        actual = _sha256(path)
        if actual != expected:
            raise ValueError(f"Manifest digest mismatch for {relative}.")
    return True
