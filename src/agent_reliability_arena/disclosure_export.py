from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .transports import verify_transport_ledger
from .transports.base import canonical_json_sha256


INDEX_FILENAME = "private-evidence-index.json"
INDEX_SCHEMA = "arena-private-evidence-index-v1"
EXPORT_SCHEMA = "arena-disclosure-safe-export-v1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_WINDOWS_ABSOLUTE = re.compile(r"(?:^|\s)[A-Za-z]:\\")
_SENSITIVE_PATTERNS = (
    re.compile(r"sensitive_marker_", re.IGNORECASE),
    re.compile(r"authorization\s*:", re.IGNORECASE),
    re.compile(r"bearer\s+[A-Za-z0-9]", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"private prompt sentence", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{8,}", re.IGNORECASE),
)
_PROHIBITED_PUBLIC_KEYS = {
    "instructions",
    "input_text",
    "output_text",
    "refusal_text",
    "provider_request_id",
    "client_request_id",
    "response_id",
    "error_message",
    "role_calls",
    "payload",
    "files",
    "operator_notes",
}
_REDACTION_RECORD = {
    "authentication_material": "excluded",
    "local_machine_identifiers": "excluded",
    "operator_notes": "excluded",
    "private_file_manifest": "committed_by_digest_only",
    "provider_payloads": "excluded",
    "raw_transport_ledger": "committed_by_digest_only",
    "role_inputs_and_prompts": "excluded",
    "role_outputs": "excluded",
}
_USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cached_input_tokens",
    "reasoning_tokens",
)


def _json_object(text: str, name: str) -> dict[str, object]:
    def no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{name} contains duplicate key {key!r}.")
            result[key] = value
        return result

    try:
        value = json.loads(text, object_pairs_hook=no_duplicates)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} is not valid JSON.") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{name} must contain a JSON object.")
    return value


def _read_object(path: Path, name: str) -> dict[str, object]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ValueError(f"{name} must be a regular non-symlink file: {target}")
    return _json_object(target.read_text(encoding="utf-8"), name)


def _write_json_exclusive(path: Path, payload: object, mode: int) -> None:
    target = Path(path)
    if target.is_symlink():
        raise ValueError(f"Output path must not be a symlink: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags, mode)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    if os.name != "nt":
        target.chmod(mode)


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value.strip()


def _safe_digest(value: object, name: str) -> str:
    text = _required_text(value, name)
    if not _HEX64.fullmatch(text):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
    return text


def _non_negative_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer.")
    return value


def _safe_public_text(value: object, name: str, *, max_length: int = 240) -> str:
    text = _required_text(value, name)
    if len(text) > max_length or any(ord(character) < 32 for character in text):
        raise ValueError(f"{name} is not safe public text.")
    if text.startswith(("/", "~")) or "\\" in text or ".." in text or _WINDOWS_ABSOLUTE.search(text):
        raise ValueError(f"{name} contains a local or unsafe path.")
    for pattern in _SENSITIVE_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"{name} contains sensitive material.")
    return text


def _safe_run_id(value: object) -> str:
    text = _required_text(value, "run_id")
    if not _SAFE_RUN_ID.fullmatch(text) or text in {".", "..", INDEX_FILENAME}:
        raise ValueError("run_id is unsafe.")
    return text


def _scan_public_payload(value: object, path: str = "export") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string key.")
            if key.lower() in _PROHIBITED_PUBLIC_KEYS:
                raise ValueError(f"{path} contains prohibited public field {key!r}.")
            _scan_public_payload(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _scan_public_payload(item, f"{path}[{index}]")
        return
    if isinstance(value, str):
        _safe_public_text(value, path, max_length=2000)
        return
    if value is None or isinstance(value, (bool, int)):
        return
    raise ValueError(f"{path} contains a non-JSON or unsafe value.")


@dataclass(frozen=True)
class PriceSource:
    source_name: str
    source_date: str
    currency: str
    input_per_million_minor_units: int
    output_per_million_minor_units: int
    source_reference: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _safe_public_text(self.source_name, "source_name"))
        source_date = _required_text(self.source_date, "source_date")
        try:
            date.fromisoformat(source_date)
        except ValueError as exc:
            raise ValueError("source_date must be an ISO date.") from exc
        object.__setattr__(self, "source_date", source_date)
        currency = _required_text(self.currency, "currency").upper()
        if len(currency) != 3 or not currency.isascii() or not currency.isalpha():
            raise ValueError("currency must be a three-letter ASCII code.")
        object.__setattr__(self, "currency", currency)
        object.__setattr__(
            self,
            "input_per_million_minor_units",
            _non_negative_int(self.input_per_million_minor_units, "input_per_million_minor_units"),
        )
        object.__setattr__(
            self,
            "output_per_million_minor_units",
            _non_negative_int(self.output_per_million_minor_units, "output_per_million_minor_units"),
        )
        object.__setattr__(
            self,
            "source_reference",
            _safe_public_text(self.source_reference, "source_reference"),
        )

    @classmethod
    def from_dict(cls, raw: object) -> "PriceSource":
        fields = {
            "source_name",
            "source_date",
            "currency",
            "input_per_million_minor_units",
            "output_per_million_minor_units",
            "source_reference",
        }
        if not isinstance(raw, dict) or set(raw) != fields:
            raise ValueError("Price source must contain exactly the documented fields.")
        return cls(**raw)  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, object]:
        return {
            "source_name": self.source_name,
            "source_date": self.source_date,
            "currency": self.currency,
            "input_per_million_minor_units": self.input_per_million_minor_units,
            "output_per_million_minor_units": self.output_per_million_minor_units,
            "source_reference": self.source_reference,
        }


def _discover_runs(root: Path, ignored_index: Path | None = None) -> list[Path]:
    private_root = Path(root)
    if private_root.is_symlink() or not private_root.is_dir():
        raise ValueError("Private evidence root must be a regular directory.")
    ignored = ignored_index.resolve() if ignored_index is not None and ignored_index.exists() else None
    runs: list[Path] = []
    for child in private_root.iterdir():
        if ignored is not None and child.resolve() == ignored:
            continue
        if child.name == INDEX_FILENAME and child.is_file():
            continue
        if child.is_symlink():
            raise ValueError(f"Private evidence root contains a symlink: {child.name}")
        if not child.is_dir():
            raise ValueError("Private evidence root may contain only run directories and its index.")
        _safe_run_id(child.name)
        runs.append(child)
    if not runs:
        raise ValueError("Private evidence root contains no run directories.")
    return sorted(runs, key=lambda path: path.name)


def _file_manifest(run_root: Path) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    for path in sorted(run_root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise ValueError(f"Private run contains a symlink: {path.relative_to(run_root)}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"Private run contains a non-regular file: {path.relative_to(run_root)}")
        raw = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(run_root).as_posix(),
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if not files:
        raise ValueError(f"Private run contains no evidence files: {run_root.name}")
    return files


def _run_status(run_root: Path) -> str:
    completed = (run_root / "verification-summary.json").is_file()
    aborted = (run_root / "abort.json").is_file()
    if completed == aborted:
        raise ValueError(f"Private run {run_root.name!r} must contain exactly one final status artifact.")
    return "completed" if completed else "aborted"


def _build_run_index(run_root: Path) -> dict[str, object]:
    run_id = _safe_run_id(run_root.name)
    status = _run_status(run_root)
    files = _file_manifest(run_root)
    file_manifest_digest = canonical_json_sha256(files)
    ledger_path = run_root / "transport-calls.jsonl"
    ledger_sha256: str | None = None
    if ledger_path.exists():
        ledger_sha256 = _safe_digest(
            verify_transport_ledger(ledger_path)["ledger_sha256"],
            "ledger_sha256",
        )
    elif status == "completed":
        raise ValueError(f"Completed private run {run_id!r} has no transport ledger.")
    commitment_source = {
        "run_id": run_id,
        "status": status,
        "file_count": len(files),
        "file_manifest_digest": file_manifest_digest,
        "ledger_sha256": ledger_sha256,
    }
    return {
        **commitment_source,
        "source_commitment_sha256": canonical_json_sha256(commitment_source),
    }


def _build_index(private_root: Path, ignored_index: Path | None = None) -> dict[str, object]:
    runs = [_build_run_index(run) for run in _discover_runs(private_root, ignored_index)]
    unsigned = {"schema_version": INDEX_SCHEMA, "runs": runs}
    return {**unsigned, "index_digest": canonical_json_sha256(unsigned)}


def write_private_evidence_index(private_root: Path) -> dict[str, object]:
    root = Path(private_root)
    target = root / INDEX_FILENAME
    if target.exists() or target.is_symlink():
        raise ValueError("Private evidence index already exists and is immutable.")
    index = _build_index(root)
    _write_json_exclusive(target, index, 0o600)
    return index


def _load_and_verify_index(private_root: Path, index_path: Path) -> dict[str, object]:
    index = _read_object(index_path, "private evidence index")
    if set(index) != {"schema_version", "runs", "index_digest"} or index.get("schema_version") != INDEX_SCHEMA:
        raise ValueError("Private evidence index shape or schema is invalid.")
    unsigned = dict(index)
    digest = unsigned.pop("index_digest")
    if canonical_json_sha256(unsigned) != _safe_digest(digest, "index_digest"):
        raise ValueError("Private evidence index digest mismatch.")
    expected_runs = index.get("runs")
    if not isinstance(expected_runs, list) or not expected_runs:
        raise ValueError("Private evidence index runs are invalid.")
    expected_by_id: dict[str, dict[str, object]] = {}
    required = {
        "run_id",
        "status",
        "file_count",
        "file_manifest_digest",
        "ledger_sha256",
        "source_commitment_sha256",
    }
    for row in expected_runs:
        if not isinstance(row, dict) or set(row) != required:
            raise ValueError("Private evidence index run shape is invalid.")
        run_id = _safe_run_id(row.get("run_id"))
        if run_id in expected_by_id:
            raise ValueError("Private evidence index contains duplicate run IDs.")
        expected_by_id[run_id] = row

    current = _build_index(Path(private_root), Path(index_path))
    current_by_id = {str(row["run_id"]): row for row in current["runs"]}
    if set(current_by_id) != set(expected_by_id):
        raise ValueError("Private evidence run set differs from the committed index.")
    for run_id, expected in expected_by_id.items():
        actual = current_by_id[run_id]
        if actual["source_commitment_sha256"] != expected["source_commitment_sha256"]:
            raise ValueError(f"Private evidence source commitment mismatch for run {run_id!r}.")
        if actual != expected:
            raise ValueError(f"Private evidence index metadata mismatch for run {run_id!r}.")
    return index


def _ledger_rows(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    summary = verify_transport_ledger(path)
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = _json_object(line, "transport ledger record")
        rows.append(row)
    return summary, rows


def _public_usage(summary: dict[str, object], rows: list[dict[str, object]]) -> dict[str, object]:
    usage = {key: 0 for key in _USAGE_KEYS}
    latency_ms = 0
    provider_processing_ms = 0
    provider_processing_reported_calls = 0
    error_categories: dict[str, int] = {}
    seeds: set[int] = set()
    conditions: dict[str, int] = {}
    roles: dict[str, int] = {}
    providers: set[str] = set()
    model_ids: set[str] = set()
    model_versions: set[str] = set()
    prompt_versions: set[str] = set()
    scenario_ids: set[str] = set()
    experiment_ids: set[str] = set()
    config_digests: set[str] = set()
    contract_digests: set[str] = set()
    prompt_catalog_digests: set[str] = set()

    for row in rows:
        request = row["request"]
        assert isinstance(request, dict)
        seed = request.get("seed")
        seeds.add(_non_negative_int(seed, "ledger request seed"))
        condition = _safe_public_text(request.get("condition"), "ledger condition")
        role = _safe_public_text(request.get("role"), "ledger role")
        conditions[condition] = conditions.get(condition, 0) + 1
        roles[role] = roles.get(role, 0) + 1
        model_ids.add(_safe_public_text(request.get("model_id"), "ledger model_id"))
        model_versions.add(_safe_public_text(request.get("model_version"), "ledger model_version"))
        prompt_versions.add(_safe_public_text(request.get("prompt_version"), "ledger prompt_version"))
        provider = _safe_public_text(row.get("provider"), "ledger provider")
        providers.add(provider)
        metadata = request.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError("Ledger request metadata is invalid.")
        scenario_ids.add(_safe_public_text(metadata.get("scenario_id"), "ledger scenario_id"))
        experiment_ids.add(_safe_public_text(metadata.get("experiment_id"), "ledger experiment_id"))
        config_digests.add(_safe_digest(metadata.get("config_digest"), "ledger config_digest"))
        contract_digests.add(_safe_digest(metadata.get("contract_digest"), "ledger contract_digest"))
        prompt_catalog_digests.add(
            _safe_digest(metadata.get("prompt_catalog_digest"), "ledger prompt_catalog_digest")
        )

        if row.get("outcome_type") == "result":
            result = row.get("result")
            if not isinstance(result, dict):
                raise ValueError("Ledger result is invalid.")
            result_usage = result.get("usage")
            if not isinstance(result_usage, dict) or set(result_usage) != set(_USAGE_KEYS):
                raise ValueError("Ledger usage is invalid.")
            for key in _USAGE_KEYS:
                usage[key] += _non_negative_int(result_usage.get(key), f"ledger usage {key}")
            latency_ms += _non_negative_int(result.get("latency_ms"), "ledger latency_ms")
            processing = result.get("provider_processing_ms")
            if processing is not None:
                provider_processing_ms += _non_negative_int(processing, "provider_processing_ms")
                provider_processing_reported_calls += 1
        else:
            error = row.get("error")
            if not isinstance(error, dict):
                raise ValueError("Ledger error is invalid.")
            category = _safe_public_text(error.get("category"), "ledger error category")
            error_categories[category] = error_categories.get(category, 0) + 1

    def one(values: set[str], name: str) -> str:
        if len(values) != 1:
            raise ValueError(f"Private run contains inconsistent {name} values.")
        return next(iter(values))

    return {
        **usage,
        "wall_clock_latency_ms": latency_ms,
        "provider_processing_ms": provider_processing_ms,
        "provider_processing_reported_calls": provider_processing_reported_calls,
        "result_records": int(summary["results"]),
        "error_records": int(summary["errors"]),
        "error_categories": dict(sorted(error_categories.items())),
        "seeds": sorted(seeds),
        "condition_call_counts": dict(sorted(conditions.items())),
        "role_call_counts": dict(sorted(roles.items())),
        "provider": one(providers, "provider"),
        "model_id": one(model_ids, "model_id"),
        "model_version": one(model_versions, "model_version"),
        "prompt_version": one(prompt_versions, "prompt_version"),
        "scenario_id": one(scenario_ids, "scenario_id"),
        "experiment_id": one(experiment_ids, "experiment_id"),
        "config_digest": one(config_digests, "config_digest"),
        "contract_digest": one(contract_digests, "contract_digest"),
        "prompt_catalog_digest": one(prompt_catalog_digests, "prompt_catalog_digest"),
    }


def _verify_private_metadata(run_root: Path, final: dict[str, object], ledger: dict[str, object]) -> dict[str, object]:
    start = _read_object(run_root / "run-start.json", "run start")
    preflight = _read_object(run_root / "preflight.json", "pilot preflight")
    policy = _read_object(run_root / "policy.json", "pilot policy")

    preflight_unsigned = dict(preflight)
    preflight_digest = preflight_unsigned.pop("manifest_digest", None)
    if canonical_json_sha256(preflight_unsigned) != _safe_digest(preflight_digest, "preflight manifest digest"):
        raise ValueError("Private preflight manifest digest mismatch.")
    policy_digest = canonical_json_sha256(policy)

    checks = {
        "provider": ledger["provider"],
        "model_id": ledger["model_id"],
        "model_version": ledger["model_version"],
        "prompt_version": ledger["prompt_version"],
        "scenario_id": ledger["scenario_id"],
        "config_digest": ledger["config_digest"],
        "contract_digest": ledger["contract_digest"],
        "prompt_catalog_digest": ledger["prompt_catalog_digest"],
    }
    for name, expected in checks.items():
        for document_name, document in (("run-start", start), ("final", final)):
            if document.get(name) != expected:
                raise ValueError(f"{document_name} {name} does not match verified ledger evidence.")
    if start.get("policy_digest") != policy_digest or final.get("policy_digest") != policy_digest:
        raise ValueError("Private policy digest mismatch.")
    if start.get("preflight_manifest_digest") != preflight_digest or final.get("preflight_manifest_digest") != preflight_digest:
        raise ValueError("Private preflight digest reference mismatch.")
    return {
        "provider": ledger["provider"],
        "model_id": ledger["model_id"],
        "model_version": ledger["model_version"],
        "prompt_version": ledger["prompt_version"],
        "scenario_id": ledger["scenario_id"],
        "experiment_id": ledger["experiment_id"],
        "config_digest": ledger["config_digest"],
        "contract_digest": ledger["contract_digest"],
        "prompt_catalog_digest": ledger["prompt_catalog_digest"],
        "policy_digest": policy_digest,
        "preflight_manifest_digest": preflight_digest,
        "seeds": ledger["seeds"],
        "condition_order": list(start.get("condition_order", [])),
    }


def _public_condition(raw: object, condition: str, source_commitment: str, ledger_sha256: str) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise ValueError(f"Private {condition} result is invalid.")
    final_status = _safe_public_text(raw.get("final_status"), f"{condition} final_status")
    completion_claimed = raw.get("completion_claimed")
    if not isinstance(completion_claimed, bool):
        raise ValueError(f"Private {condition} completion_claimed is invalid.")
    verified_complete = final_status == "VERIFIED_COMPLETE"
    false_completion = completion_claimed and not verified_complete
    silent_verified_completion = verified_complete and not completion_claimed
    for name, derived in (
        ("verified_complete", verified_complete),
        ("false_completion", false_completion),
        ("silent_verified_completion", silent_verified_completion),
    ):
        if raw.get(name) is not derived:
            raise ValueError(f"Private {condition} {name} conflicts with authoritative status.")
    logical_calls = _non_negative_int(raw.get("logical_model_calls"), f"{condition} logical_model_calls")
    attempts = raw.get("attempts")
    if not isinstance(attempts, list):
        raise ValueError(f"Private {condition} attempts are invalid.")
    recovered = raw.get("recovered")
    security_rejected = raw.get("security_rejected")
    if not isinstance(recovered, bool) or not isinstance(security_rejected, bool):
        raise ValueError(f"Private {condition} flags are invalid.")
    return {
        "final_status": final_status,
        "completion_claimed": completion_claimed,
        "verified_complete": verified_complete,
        "false_completion": false_completion,
        "silent_verified_completion": silent_verified_completion,
        "logical_model_calls": logical_calls,
        "attempts": len(attempts),
        "recovered": recovered,
        "security_rejected": security_rejected,
        "evidence_refs": [
            f"private-source:{source_commitment}#conditions/{condition}",
            f"private-ledger:{ledger_sha256}#{condition}",
        ],
    }


def _public_run(private_root: Path, index_row: dict[str, object]) -> dict[str, object]:
    run_id = _safe_run_id(index_row["run_id"])
    run_root = private_root / run_id
    status = index_row["status"]
    if status not in {"completed", "aborted"}:
        raise ValueError("Private index status is invalid.")
    source_commitment = _safe_digest(index_row["source_commitment_sha256"], "source commitment")
    file_manifest_digest = _safe_digest(index_row["file_manifest_digest"], "file manifest digest")
    ledger_path = run_root / "transport-calls.jsonl"
    if not ledger_path.is_file():
        raise ValueError("Disclosure export requires a verified ledger for every indexed run.")
    ledger_summary, ledger_rows = _ledger_rows(ledger_path)
    ledger_sha256 = _safe_digest(ledger_summary["ledger_sha256"], "ledger sha256")
    if index_row.get("ledger_sha256") != ledger_sha256:
        raise ValueError("Private index ledger digest does not match verified ledger.")
    ledger = _public_usage(ledger_summary, ledger_rows)

    if status == "completed":
        final = _read_object(run_root / "verification-summary.json", "verification summary")
    else:
        final = _read_object(run_root / "abort.json", "abort summary")
    common = _verify_private_metadata(run_root, final, ledger)
    usage = {key: ledger[key] for key in _USAGE_KEYS}
    usage.update(
        {
            "wall_clock_latency_ms": ledger["wall_clock_latency_ms"],
            "provider_processing_ms": ledger["provider_processing_ms"],
            "provider_processing_reported_calls": ledger["provider_processing_reported_calls"],
            "result_records": ledger["result_records"],
            "error_records": ledger["error_records"],
            "error_categories": ledger["error_categories"],
        }
    )
    public: dict[str, object] = {
        "run_id": run_id,
        "status": status,
        **common,
        "fairness": {
            "same_provider_across_calls": True,
            "same_model_across_calls": True,
            "same_model_version_across_calls": True,
            "same_prompt_version_across_calls": True,
            "same_scenario_across_calls": True,
            "same_seed_across_calls": len(common["seeds"]) == 1,
            "condition_order": common["condition_order"],
        },
        "usage": usage,
        "private_file_manifest_digest": file_manifest_digest,
        "private_ledger_sha256": ledger_sha256,
        "source_commitment_sha256": source_commitment,
        "comparative_claim_permitted": False,
    }

    if status == "completed":
        if final.get("status") != "completed" or final.get("comparative_claim_permitted") is not False:
            raise ValueError("Private completed summary claims boundary is invalid.")
        conditions = final.get("conditions")
        if not isinstance(conditions, dict) or set(conditions) != {"general", "specialist"}:
            raise ValueError("Private completed conditions are invalid.")
        public_conditions = {
            condition: _public_condition(conditions[condition], condition, source_commitment, ledger_sha256)
            for condition in ("general", "specialist")
        }
        call_counts = ledger["condition_call_counts"]
        assert isinstance(call_counts, dict)
        for condition, result in public_conditions.items():
            if result["logical_model_calls"] != call_counts.get(condition, 0):
                raise ValueError(f"Private {condition} call count does not match the verified ledger.")
        if final.get("ledger") != ledger_summary:
            raise ValueError("Private completed ledger summary does not match independent verification.")
        public["conditions"] = public_conditions
        public["abort"] = None
    else:
        if final.get("status") != "aborted":
            raise ValueError("Private abort summary status is invalid.")
        if final.get("ledger") != ledger_summary:
            raise ValueError("Private abort ledger summary does not match independent verification.")
        public["conditions"] = {}
        public["abort"] = {
            "stage": _safe_public_text(final.get("stage"), "abort stage"),
            "error_type": _safe_public_text(final.get("error_type"), "abort error_type"),
            "ledger_verified": True,
        }
    return public


def _aggregate(runs: list[dict[str, object]]) -> dict[str, object]:
    aggregate: dict[str, object] = {
        "runs_total": len(runs),
        "completed_runs": 0,
        "aborted_runs": 0,
        "conditions_total": 0,
        "verified_complete_conditions": 0,
        "false_completion_conditions": 0,
        "silent_verified_completion_conditions": 0,
        "recovered_conditions": 0,
        "security_rejected_conditions": 0,
        "transport_result_records": 0,
        "transport_error_records": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cached_input_tokens": 0,
        "reasoning_tokens": 0,
        "wall_clock_latency_ms": 0,
        "provider_processing_ms": 0,
        "provider_processing_reported_calls": 0,
    }
    for run in runs:
        status = run["status"]
        aggregate[f"{status}_runs"] = int(aggregate[f"{status}_runs"]) + 1
        usage = run["usage"]
        assert isinstance(usage, dict)
        for public_key, usage_key in (
            ("transport_result_records", "result_records"),
            ("transport_error_records", "error_records"),
            ("input_tokens", "input_tokens"),
            ("output_tokens", "output_tokens"),
            ("total_tokens", "total_tokens"),
            ("cached_input_tokens", "cached_input_tokens"),
            ("reasoning_tokens", "reasoning_tokens"),
            ("wall_clock_latency_ms", "wall_clock_latency_ms"),
            ("provider_processing_ms", "provider_processing_ms"),
            ("provider_processing_reported_calls", "provider_processing_reported_calls"),
        ):
            aggregate[public_key] = int(aggregate[public_key]) + int(usage[usage_key])
        conditions = run["conditions"]
        assert isinstance(conditions, dict)
        for condition in conditions.values():
            assert isinstance(condition, dict)
            aggregate["conditions_total"] = int(aggregate["conditions_total"]) + 1
            for key in (
                "verified_complete",
                "false_completion",
                "silent_verified_completion",
                "recovered",
                "security_rejected",
            ):
                target = f"{key}_conditions"
                aggregate[target] = int(aggregate[target]) + int(bool(condition[key]))
    return aggregate


def build_disclosure_safe_empirical_export(
    private_root: Path,
    *,
    index_path: Path | None = None,
    price_source: PriceSource | None = None,
) -> dict[str, object]:
    root = Path(private_root)
    index_target = Path(index_path) if index_path is not None else root / INDEX_FILENAME
    index = _load_and_verify_index(root, index_target)
    index_rows = index["runs"]
    assert isinstance(index_rows, list)
    runs = [_public_run(root, row) for row in index_rows if isinstance(row, dict)]
    runs.sort(key=lambda run: (0 if run["status"] == "completed" else 1, str(run["run_id"])))
    unsigned: dict[str, object] = {
        "schema_version": EXPORT_SCHEMA,
        "private_index_digest": index["index_digest"],
        "runs": runs,
        "aggregate": _aggregate(runs),
        "price_source": price_source.to_dict() if price_source is not None else None,
        "redaction_record": dict(_REDACTION_RECORD),
        "limitations": [
            "The private source evidence remains private and is represented by stable digests.",
            "A small or single-provider sample is not representative of general model performance.",
            "Dated price metadata is separate from measured usage and is not measured provider billing.",
            "Export and public replay perform no provider request.",
        ],
        "comparative_claim_permitted": False,
        "provider_called": False,
    }
    _scan_public_payload(unsigned)
    return {**unsigned, "bundle_digest": canonical_json_sha256(unsigned)}


def write_disclosure_safe_empirical_export(
    private_root: Path,
    output_path: Path,
    *,
    index_path: Path | None = None,
    price_source: PriceSource | None = None,
) -> dict[str, object]:
    export = build_disclosure_safe_empirical_export(
        private_root,
        index_path=index_path,
        price_source=price_source,
    )
    _write_json_exclusive(Path(output_path), export, 0o644)
    return export


def _validate_public_run(run: object) -> None:
    if not isinstance(run, dict):
        raise ValueError("Public run must be a JSON object.")
    required = {
        "run_id",
        "status",
        "provider",
        "model_id",
        "model_version",
        "prompt_version",
        "scenario_id",
        "experiment_id",
        "config_digest",
        "contract_digest",
        "prompt_catalog_digest",
        "policy_digest",
        "preflight_manifest_digest",
        "seeds",
        "condition_order",
        "fairness",
        "usage",
        "private_file_manifest_digest",
        "private_ledger_sha256",
        "source_commitment_sha256",
        "comparative_claim_permitted",
        "conditions",
        "abort",
    }
    if set(run) != required:
        raise ValueError("Public run shape is invalid.")
    _safe_run_id(run["run_id"])
    if run["status"] not in {"completed", "aborted"}:
        raise ValueError("Public run status is invalid.")
    for name in (
        "provider",
        "model_id",
        "model_version",
        "prompt_version",
        "scenario_id",
        "experiment_id",
    ):
        _safe_public_text(run[name], name)
    for name in (
        "config_digest",
        "contract_digest",
        "prompt_catalog_digest",
        "policy_digest",
        "preflight_manifest_digest",
        "private_file_manifest_digest",
        "private_ledger_sha256",
        "source_commitment_sha256",
    ):
        _safe_digest(run[name], name)
    if run["comparative_claim_permitted"] is not False:
        raise ValueError("Public run may not permit a comparative claim.")
    conditions = run["conditions"]
    if not isinstance(conditions, dict):
        raise ValueError("Public conditions are invalid.")
    if run["status"] == "completed":
        if set(conditions) != {"general", "specialist"} or run["abort"] is not None:
            raise ValueError("Public completed run shape is invalid.")
        for condition in conditions.values():
            if not isinstance(condition, dict):
                raise ValueError("Public condition is invalid.")
            status = _safe_public_text(condition.get("final_status"), "public final_status")
            claim = condition.get("completion_claimed")
            if not isinstance(claim, bool):
                raise ValueError("Public completion claim is invalid.")
            expected = {
                "verified_complete": status == "VERIFIED_COMPLETE",
                "false_completion": claim and status != "VERIFIED_COMPLETE",
                "silent_verified_completion": (not claim) and status == "VERIFIED_COMPLETE",
            }
            for name, value in expected.items():
                if condition.get(name) is not value:
                    raise ValueError("Public condition aggregate fields conflict with final status.")
    else:
        if conditions or not isinstance(run["abort"], dict):
            raise ValueError("Public aborted run shape is invalid.")


def verify_disclosure_safe_empirical_export(source: dict[str, object] | Path) -> dict[str, object]:
    export = _read_object(source, "public empirical export") if isinstance(source, Path) else source
    if not isinstance(export, dict):
        raise ValueError("Public empirical export must be a JSON object.")
    required = {
        "schema_version",
        "private_index_digest",
        "runs",
        "aggregate",
        "price_source",
        "redaction_record",
        "limitations",
        "comparative_claim_permitted",
        "provider_called",
        "bundle_digest",
    }
    if set(export) != required or export.get("schema_version") != EXPORT_SCHEMA:
        raise ValueError("Public empirical export shape or schema is invalid.")
    unsigned = dict(export)
    supplied_digest = unsigned.pop("bundle_digest")
    if canonical_json_sha256(unsigned) != _safe_digest(supplied_digest, "bundle digest"):
        raise ValueError("Public bundle digest mismatch.")
    _safe_digest(export["private_index_digest"], "private index digest")
    if export["comparative_claim_permitted"] is not False or export["provider_called"] is not False:
        raise ValueError("Public export claims boundary is invalid.")
    if export["redaction_record"] != _REDACTION_RECORD:
        raise ValueError("Public redaction record is invalid.")
    runs = export.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("Public export runs are invalid.")
    for run in runs:
        _validate_public_run(run)
    expected_aggregate = _aggregate(runs)  # type: ignore[arg-type]
    if export.get("aggregate") != expected_aggregate:
        raise ValueError("Public aggregate does not match public run outcomes.")
    price = export.get("price_source")
    if price is not None:
        PriceSource.from_dict(price)
    _scan_public_payload(unsigned)
    return {
        "schema_version": EXPORT_SCHEMA,
        "bundle_digest_verified": True,
        "runs_verified": len(runs),
        "completed_runs": expected_aggregate["completed_runs"],
        "aborted_runs": expected_aggregate["aborted_runs"],
        "provider_called": False,
    }
