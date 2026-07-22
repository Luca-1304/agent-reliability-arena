from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .transports import verify_transport_ledger
from .transports.base import canonical_json_sha256


INDEX_FILENAME = "private-evidence-index.json"
INDEX_SCHEMA = "arena-private-evidence-index-v1"
EXPORT_SCHEMA = "arena-disclosure-safe-export-v1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_WINDOWS_PATH = re.compile(r"(?:^|\s)[A-Za-z]:\\")
_SENSITIVE = (
    re.compile(r"sensitive_marker_", re.IGNORECASE),
    re.compile(r"authorization\s*:", re.IGNORECASE),
    re.compile(r"bearer\s+[A-Za-z0-9]", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"private prompt sentence", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{8,}", re.IGNORECASE),
)
_PROHIBITED_KEYS = {
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
_REDACTIONS = {
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


def _decode_object(text: str, name: str) -> dict[str, object]:
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
    return _decode_object(target.read_text(encoding="utf-8"), name)


def _write_exclusive(path: Path, payload: object, mode: int) -> None:
    target = Path(path)
    if target.is_symlink() or target.exists():
        raise ValueError(f"Output path must be new and non-symlinked: {target}")
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


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value.strip()


def _digest(value: object, name: str) -> str:
    text = _text(value, name)
    if not _HEX64.fullmatch(text):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
    return text


def _integer(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer.")
    return value


def _safe_text(value: object, name: str, *, limit: int = 2000) -> str:
    text = _text(value, name)
    if len(text) > limit or any(ord(character) < 32 for character in text):
        raise ValueError(f"{name} is not safe public text.")
    if text.startswith(("/", "~")) or "\\" in text or ".." in text or _WINDOWS_PATH.search(text):
        raise ValueError(f"{name} contains a local or unsafe path.")
    for pattern in _SENSITIVE:
        if pattern.search(text):
            raise ValueError(f"{name} contains sensitive material.")
    return text


def _run_id(value: object) -> str:
    text = _text(value, "run_id")
    if not _RUN_ID.fullmatch(text) or text in {".", "..", INDEX_FILENAME}:
        raise ValueError("run_id is unsafe.")
    return text


def _scan_public(value: object, path: str = "export") -> None:
    if isinstance(value, dict):
        is_redaction_record = path == "export.redaction_record"
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string key.")
            if not is_redaction_record and key.lower() in _PROHIBITED_KEYS:
                raise ValueError(f"{path} contains prohibited public field {key!r}.")
            _safe_text(key, f"{path} key")
            _scan_public(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _scan_public(item, f"{path}[{index}]")
        return
    if isinstance(value, str):
        _safe_text(value, path)
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
        object.__setattr__(self, "source_name", _safe_text(self.source_name, "source_name"))
        source_date = _text(self.source_date, "source_date")
        try:
            date.fromisoformat(source_date)
        except ValueError as exc:
            raise ValueError("source_date must be an ISO date.") from exc
        object.__setattr__(self, "source_date", source_date)
        currency = _text(self.currency, "currency").upper()
        if len(currency) != 3 or not currency.isascii() or not currency.isalpha():
            raise ValueError("currency must be a three-letter ASCII code.")
        object.__setattr__(self, "currency", currency)
        object.__setattr__(
            self,
            "input_per_million_minor_units",
            _integer(self.input_per_million_minor_units, "input_per_million_minor_units"),
        )
        object.__setattr__(
            self,
            "output_per_million_minor_units",
            _integer(self.output_per_million_minor_units, "output_per_million_minor_units"),
        )
        object.__setattr__(
            self,
            "source_reference",
            _safe_text(self.source_reference, "source_reference"),
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
        return cls(
            source_name=raw["source_name"],
            source_date=raw["source_date"],
            currency=raw["currency"],
            input_per_million_minor_units=raw["input_per_million_minor_units"],
            output_per_million_minor_units=raw["output_per_million_minor_units"],
            source_reference=raw["source_reference"],
        )  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, object]:
        return {
            "source_name": self.source_name,
            "source_date": self.source_date,
            "currency": self.currency,
            "input_per_million_minor_units": self.input_per_million_minor_units,
            "output_per_million_minor_units": self.output_per_million_minor_units,
            "source_reference": self.source_reference,
        }


def _discover(root: Path, index_path: Path | None = None) -> list[Path]:
    private_root = Path(root)
    if private_root.is_symlink() or not private_root.is_dir():
        raise ValueError("Private evidence root must be a regular directory.")
    ignored = index_path.resolve() if index_path is not None and index_path.exists() else None
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
        _run_id(child.name)
        runs.append(child)
    if not runs:
        raise ValueError("Private evidence root contains no run directories.")
    return sorted(runs, key=lambda path: path.name)


def _manifest(run_root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(run_root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise ValueError(f"Private run contains a symlink: {path.relative_to(run_root)}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"Private run contains a non-regular file: {path.relative_to(run_root)}")
        raw = path.read_bytes()
        rows.append(
            {
                "path": path.relative_to(run_root).as_posix(),
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if not rows:
        raise ValueError(f"Private run contains no evidence files: {run_root.name}")
    return rows


def _status(run_root: Path) -> str:
    completed = (run_root / "verification-summary.json").is_file()
    aborted = (run_root / "abort.json").is_file()
    if completed == aborted:
        raise ValueError(f"Private run {run_root.name!r} must contain exactly one final status artifact.")
    return "completed" if completed else "aborted"


def _index_row(run_root: Path) -> dict[str, object]:
    run_name = _run_id(run_root.name)
    status = _status(run_root)
    files = _manifest(run_root)
    file_digest = canonical_json_sha256(files)
    ledger_path = run_root / "transport-calls.jsonl"
    ledger_digest: str | None = None
    if ledger_path.is_file():
        ledger_digest = _digest(verify_transport_ledger(ledger_path)["ledger_sha256"], "ledger_sha256")
    elif status == "completed":
        raise ValueError(f"Completed private run {run_name!r} has no transport ledger.")
    source = {
        "run_id": run_name,
        "status": status,
        "file_count": len(files),
        "file_manifest_digest": file_digest,
        "ledger_sha256": ledger_digest,
    }
    return {**source, "source_commitment_sha256": canonical_json_sha256(source)}


def _make_index(root: Path, index_path: Path | None = None) -> dict[str, object]:
    rows = [_index_row(run) for run in _discover(root, index_path)]
    unsigned = {"schema_version": INDEX_SCHEMA, "runs": rows}
    return {**unsigned, "index_digest": canonical_json_sha256(unsigned)}


def write_private_evidence_index(private_root: Path) -> dict[str, object]:
    root = Path(private_root)
    target = root / INDEX_FILENAME
    if target.exists() or target.is_symlink():
        raise ValueError("Private evidence index already exists and is immutable.")
    index = _make_index(root)
    _write_exclusive(target, index, 0o600)
    return index


def _verify_index(root: Path, index_path: Path) -> dict[str, object]:
    index = _read_object(index_path, "private evidence index")
    if set(index) != {"schema_version", "runs", "index_digest"} or index.get("schema_version") != INDEX_SCHEMA:
        raise ValueError("Private evidence index shape or schema is invalid.")
    unsigned = dict(index)
    supplied = unsigned.pop("index_digest", None)
    if canonical_json_sha256(unsigned) != _digest(supplied, "index_digest"):
        raise ValueError("Private evidence index digest mismatch.")
    rows = index.get("runs")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Private evidence index runs are invalid.")
    required = {
        "run_id",
        "status",
        "file_count",
        "file_manifest_digest",
        "ledger_sha256",
        "source_commitment_sha256",
    }
    expected: dict[str, dict[str, object]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != required:
            raise ValueError("Private evidence index run shape is invalid.")
        name = _run_id(row.get("run_id"))
        if name in expected:
            raise ValueError("Private evidence index contains duplicate run IDs.")
        expected[name] = row

    current_dirs = _discover(root, index_path)
    current_names = {path.name for path in current_dirs}
    if current_names != set(expected):
        raise ValueError("Private evidence run set differs from the committed index.")
    current = {path.name: _index_row(path) for path in current_dirs}
    for name, expected_row in expected.items():
        if current[name]["source_commitment_sha256"] != expected_row["source_commitment_sha256"]:
            raise ValueError(f"Private evidence source commitment mismatch for run {name!r}.")
        if current[name] != expected_row:
            raise ValueError(f"Private evidence index metadata mismatch for run {name!r}.")
    return index


def _ledger(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    summary = verify_transport_ledger(path)
    rows = [_decode_object(line, "transport ledger record") for line in path.read_text(encoding="utf-8").splitlines()]
    return summary, rows


def _one(values: set[str], name: str) -> str:
    if len(values) != 1:
        raise ValueError(f"Private run contains inconsistent {name} values.")
    return next(iter(values))


def _ledger_facts(summary: dict[str, object], rows: list[dict[str, object]]) -> dict[str, object]:
    totals = {key: 0 for key in _USAGE_KEYS}
    latency = 0
    processing = 0
    processing_calls = 0
    errors: dict[str, int] = {}
    seeds: set[int] = set()
    condition_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    providers: set[str] = set()
    model_ids: set[str] = set()
    model_versions: set[str] = set()
    prompt_versions: set[str] = set()
    scenarios: set[str] = set()
    experiments: set[str] = set()
    configs: set[str] = set()
    contracts: set[str] = set()
    catalogues: set[str] = set()

    for row in rows:
        request = row.get("request")
        if not isinstance(request, dict):
            raise ValueError("Ledger request is invalid.")
        seeds.add(_integer(request.get("seed"), "ledger seed"))
        condition = _safe_text(request.get("condition"), "ledger condition")
        role = _safe_text(request.get("role"), "ledger role")
        condition_counts[condition] = condition_counts.get(condition, 0) + 1
        role_counts[role] = role_counts.get(role, 0) + 1
        providers.add(_safe_text(row.get("provider"), "ledger provider"))
        model_ids.add(_safe_text(request.get("model_id"), "ledger model_id"))
        model_versions.add(_safe_text(request.get("model_version"), "ledger model_version"))
        prompt_versions.add(_safe_text(request.get("prompt_version"), "ledger prompt_version"))
        metadata = request.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError("Ledger request metadata is invalid.")
        scenarios.add(_safe_text(metadata.get("scenario_id"), "ledger scenario_id"))
        experiments.add(_safe_text(metadata.get("experiment_id"), "ledger experiment_id"))
        configs.add(_digest(metadata.get("config_digest"), "ledger config_digest"))
        contracts.add(_digest(metadata.get("contract_digest"), "ledger contract_digest"))
        catalogues.add(_digest(metadata.get("prompt_catalog_digest"), "ledger prompt_catalog_digest"))

        if row.get("outcome_type") == "result":
            result = row.get("result")
            if not isinstance(result, dict):
                raise ValueError("Ledger result is invalid.")
            usage = result.get("usage")
            if not isinstance(usage, dict) or set(usage) != set(_USAGE_KEYS):
                raise ValueError("Ledger usage is invalid.")
            for key in _USAGE_KEYS:
                totals[key] += _integer(usage.get(key), f"ledger {key}")
            latency += _integer(result.get("latency_ms"), "ledger latency_ms")
            value = result.get("provider_processing_ms")
            if value is not None:
                processing += _integer(value, "ledger provider_processing_ms")
                processing_calls += 1
        else:
            error = row.get("error")
            if not isinstance(error, dict):
                raise ValueError("Ledger error is invalid.")
            category = _safe_text(error.get("category"), "ledger error category")
            errors[category] = errors.get(category, 0) + 1

    return {
        **totals,
        "wall_clock_latency_ms": latency,
        "provider_processing_ms": processing,
        "provider_processing_reported_calls": processing_calls,
        "result_records": _integer(summary.get("results"), "ledger result records"),
        "error_records": _integer(summary.get("errors"), "ledger error records"),
        "error_categories": dict(sorted(errors.items())),
        "seeds": sorted(seeds),
        "condition_call_counts": dict(sorted(condition_counts.items())),
        "role_call_counts": dict(sorted(role_counts.items())),
        "provider": _one(providers, "provider"),
        "model_id": _one(model_ids, "model_id"),
        "model_version": _one(model_versions, "model_version"),
        "prompt_version": _one(prompt_versions, "prompt_version"),
        "scenario_id": _one(scenarios, "scenario_id"),
        "experiment_id": _one(experiments, "experiment_id"),
        "config_digest": _one(configs, "config_digest"),
        "contract_digest": _one(contracts, "contract_digest"),
        "prompt_catalog_digest": _one(catalogues, "prompt_catalog_digest"),
    }


def _common_metadata(
    run_root: Path,
    final: dict[str, object],
    facts: dict[str, object],
    *,
    completed: bool,
) -> dict[str, object]:
    start = _read_object(run_root / "run-start.json", "run start")
    preflight = _read_object(run_root / "preflight.json", "pilot preflight")
    policy = _read_object(run_root / "policy.json", "pilot policy")
    preflight_unsigned = dict(preflight)
    preflight_digest = preflight_unsigned.pop("manifest_digest", None)
    if canonical_json_sha256(preflight_unsigned) != _digest(preflight_digest, "preflight manifest digest"):
        raise ValueError("Private preflight manifest digest mismatch.")
    policy_digest = canonical_json_sha256(policy)

    checks = {
        "provider": facts["provider"],
        "model_id": facts["model_id"],
        "model_version": facts["model_version"],
        "prompt_version": facts["prompt_version"],
        "scenario_id": facts["scenario_id"],
        "config_digest": facts["config_digest"],
        "contract_digest": facts["contract_digest"],
        "prompt_catalog_digest": facts["prompt_catalog_digest"],
    }
    documents = [("run-start", start)]
    if completed:
        documents.append(("verification-summary", final))
    for name, expected in checks.items():
        for document_name, document in documents:
            if document.get(name) != expected:
                raise ValueError(f"{document_name} {name} does not match verified ledger evidence.")
    if start.get("policy_digest") != policy_digest:
        raise ValueError("Private run-start policy digest mismatch.")
    if start.get("preflight_manifest_digest") != preflight_digest:
        raise ValueError("Private run-start preflight digest mismatch.")
    if completed:
        if final.get("policy_digest") != policy_digest or final.get("preflight_manifest_digest") != preflight_digest:
            raise ValueError("Private completed digest reference mismatch.")
    else:
        gate = final.get("gate")
        if gate is not None and (not isinstance(gate, dict) or gate.get("policy_digest") != policy_digest):
            raise ValueError("Private abort gate policy digest mismatch.")

    order = start.get("condition_order")
    if not isinstance(order, list) or not all(isinstance(item, str) for item in order):
        raise ValueError("Private condition order is invalid.")
    return {
        "provider": facts["provider"],
        "model_id": facts["model_id"],
        "model_version": facts["model_version"],
        "prompt_version": facts["prompt_version"],
        "scenario_id": facts["scenario_id"],
        "experiment_id": facts["experiment_id"],
        "config_digest": facts["config_digest"],
        "contract_digest": facts["contract_digest"],
        "prompt_catalog_digest": facts["prompt_catalog_digest"],
        "policy_digest": policy_digest,
        "preflight_manifest_digest": preflight_digest,
        "seeds": facts["seeds"],
        "condition_order": order,
    }


def _condition(raw: object, name: str, source: str, ledger_digest: str) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise ValueError(f"Private {name} result is invalid.")
    final_status = _safe_text(raw.get("final_status"), f"{name} final status")
    claim = raw.get("completion_claimed")
    if not isinstance(claim, bool):
        raise ValueError(f"Private {name} completion claim is invalid.")
    verified = final_status == "VERIFIED_COMPLETE"
    false_completion = claim and not verified
    silent = verified and not claim
    for key, expected in (
        ("verified_complete", verified),
        ("false_completion", false_completion),
        ("silent_verified_completion", silent),
    ):
        if raw.get(key) is not expected:
            raise ValueError(f"Private {name} {key} conflicts with final status.")
    attempts = raw.get("attempts")
    if not isinstance(attempts, list):
        raise ValueError(f"Private {name} attempts are invalid.")
    recovered = raw.get("recovered")
    security = raw.get("security_rejected")
    if not isinstance(recovered, bool) or not isinstance(security, bool):
        raise ValueError(f"Private {name} flags are invalid.")
    return {
        "final_status": final_status,
        "completion_claimed": claim,
        "verified_complete": verified,
        "false_completion": false_completion,
        "silent_verified_completion": silent,
        "logical_model_calls": _integer(raw.get("logical_model_calls"), f"{name} logical calls"),
        "attempts": len(attempts),
        "recovered": recovered,
        "security_rejected": security,
        "evidence_refs": [
            f"private-source:{source}#conditions/{name}",
            f"private-ledger:{ledger_digest}#{name}",
        ],
    }


def _public_run(root: Path, row: dict[str, object]) -> dict[str, object]:
    name = _run_id(row.get("run_id"))
    status = row.get("status")
    if status not in {"completed", "aborted"}:
        raise ValueError("Private index status is invalid.")
    source = _digest(row.get("source_commitment_sha256"), "source commitment")
    file_digest = _digest(row.get("file_manifest_digest"), "file manifest digest")
    run_root = root / name
    ledger_summary, ledger_rows = _ledger(run_root / "transport-calls.jsonl")
    ledger_digest = _digest(ledger_summary.get("ledger_sha256"), "ledger sha256")
    if row.get("ledger_sha256") != ledger_digest:
        raise ValueError("Private index ledger digest does not match verified ledger.")
    facts = _ledger_facts(ledger_summary, ledger_rows)
    final = _read_object(
        run_root / ("verification-summary.json" if status == "completed" else "abort.json"),
        "private final evidence",
    )
    common = _common_metadata(run_root, final, facts, completed=status == "completed")
    usage = {key: facts[key] for key in _USAGE_KEYS}
    usage.update(
        {
            "wall_clock_latency_ms": facts["wall_clock_latency_ms"],
            "provider_processing_ms": facts["provider_processing_ms"],
            "provider_processing_reported_calls": facts["provider_processing_reported_calls"],
            "result_records": facts["result_records"],
            "error_records": facts["error_records"],
            "error_categories": facts["error_categories"],
        }
    )
    public: dict[str, object] = {
        "run_id": name,
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
        "private_file_manifest_digest": file_digest,
        "private_ledger_sha256": ledger_digest,
        "source_commitment_sha256": source,
        "comparative_claim_permitted": False,
    }
    if status == "completed":
        if final.get("status") != "completed" or final.get("comparative_claim_permitted") is not False:
            raise ValueError("Private completed claims boundary is invalid.")
        conditions = final.get("conditions")
        if not isinstance(conditions, dict) or set(conditions) != {"general", "specialist"}:
            raise ValueError("Private completed conditions are invalid.")
        public_conditions = {
            condition_name: _condition(conditions[condition_name], condition_name, source, ledger_digest)
            for condition_name in ("general", "specialist")
        }
        counts = facts["condition_call_counts"]
        if not isinstance(counts, dict):
            raise ValueError("Verified condition call counts are invalid.")
        for condition_name, condition in public_conditions.items():
            if condition["logical_model_calls"] != counts.get(condition_name, 0):
                raise ValueError(f"Private {condition_name} call count does not match verified ledger.")
        if final.get("ledger") != ledger_summary:
            raise ValueError("Private completed ledger summary does not match independent verification.")
        public["conditions"] = public_conditions
        public["abort"] = None
    else:
        if final.get("status") != "aborted" or final.get("ledger") != ledger_summary:
            raise ValueError("Private abort evidence does not match independent ledger verification.")
        public["conditions"] = {}
        public["abort"] = {
            "stage": _safe_text(final.get("stage"), "abort stage"),
            "error_type": _safe_text(final.get("error_type"), "abort error type"),
            "ledger_verified": True,
        }
    return public


def _aggregate(runs: list[dict[str, object]]) -> dict[str, object]:
    aggregate: dict[str, int] = {
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
        status = run.get("status")
        if status not in {"completed", "aborted"}:
            raise ValueError("Public run status is invalid for aggregate reconstruction.")
        aggregate[f"{status}_runs"] += 1
        usage = run.get("usage")
        if not isinstance(usage, dict):
            raise ValueError("Public usage is invalid for aggregate reconstruction.")
        mapping = {
            "transport_result_records": "result_records",
            "transport_error_records": "error_records",
            "input_tokens": "input_tokens",
            "output_tokens": "output_tokens",
            "total_tokens": "total_tokens",
            "cached_input_tokens": "cached_input_tokens",
            "reasoning_tokens": "reasoning_tokens",
            "wall_clock_latency_ms": "wall_clock_latency_ms",
            "provider_processing_ms": "provider_processing_ms",
            "provider_processing_reported_calls": "provider_processing_reported_calls",
        }
        for aggregate_key, usage_key in mapping.items():
            aggregate[aggregate_key] += _integer(usage.get(usage_key), f"public usage {usage_key}")
        conditions = run.get("conditions")
        if not isinstance(conditions, dict):
            raise ValueError("Public conditions are invalid for aggregate reconstruction.")
        for condition in conditions.values():
            if not isinstance(condition, dict):
                raise ValueError("Public condition is invalid for aggregate reconstruction.")
            aggregate["conditions_total"] += 1
            for key in (
                "verified_complete",
                "false_completion",
                "silent_verified_completion",
                "recovered",
                "security_rejected",
            ):
                if not isinstance(condition.get(key), bool):
                    raise ValueError(f"Public condition {key} is invalid.")
                aggregate[f"{key}_conditions"] += int(condition[key])
    return dict(aggregate)


def build_disclosure_safe_empirical_export(
    private_root: Path,
    *,
    index_path: Path | None = None,
    price_source: PriceSource | None = None,
) -> dict[str, object]:
    root = Path(private_root)
    target = Path(index_path) if index_path is not None else root / INDEX_FILENAME
    index = _verify_index(root, target)
    index_rows = index.get("runs")
    assert isinstance(index_rows, list)
    runs = [_public_run(root, row) for row in index_rows if isinstance(row, dict)]
    runs.sort(key=lambda run: (0 if run["status"] == "completed" else 1, str(run["run_id"])))
    unsigned: dict[str, object] = {
        "schema_version": EXPORT_SCHEMA,
        "private_index_digest": index["index_digest"],
        "runs": runs,
        "aggregate": _aggregate(runs),
        "price_source": price_source.to_dict() if price_source is not None else None,
        "redaction_record": dict(_REDACTIONS),
        "limitations": [
            "The private source evidence remains private and is represented by stable digests.",
            "A small or single-provider sample is not representative of general model performance.",
            "Dated price metadata is separate from measured usage and is not measured provider billing.",
            "Export and public replay perform no provider request.",
        ],
        "comparative_claim_permitted": False,
        "provider_called": False,
    }
    _scan_public(unsigned)
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
    _write_exclusive(Path(output_path), export, 0o644)
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
    _run_id(run.get("run_id"))
    if run.get("status") not in {"completed", "aborted"}:
        raise ValueError("Public run status is invalid.")
    for name in ("provider", "model_id", "model_version", "prompt_version", "scenario_id", "experiment_id"):
        _safe_text(run.get(name), name)
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
        _digest(run.get(name), name)
    if run.get("comparative_claim_permitted") is not False:
        raise ValueError("Public run may not permit comparative claims.")
    conditions = run.get("conditions")
    if not isinstance(conditions, dict):
        raise ValueError("Public run conditions are invalid.")
    if run["status"] == "completed":
        if set(conditions) != {"general", "specialist"} or run.get("abort") is not None:
            raise ValueError("Public completed run shape is invalid.")
        for condition in conditions.values():
            if not isinstance(condition, dict):
                raise ValueError("Public condition is invalid.")
            status = _safe_text(condition.get("final_status"), "public final status")
            claim = condition.get("completion_claimed")
            if not isinstance(claim, bool):
                raise ValueError("Public completion claim is invalid.")
            expected = {
                "verified_complete": status == "VERIFIED_COMPLETE",
                "false_completion": claim and status != "VERIFIED_COMPLETE",
                "silent_verified_completion": (not claim) and status == "VERIFIED_COMPLETE",
            }
            for key, value in expected.items():
                if condition.get(key) is not value:
                    raise ValueError("Public condition fields conflict with authoritative final status.")
    elif conditions or not isinstance(run.get("abort"), dict):
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
    supplied = unsigned.pop("bundle_digest", None)
    if canonical_json_sha256(unsigned) != _digest(supplied, "bundle digest"):
        raise ValueError("Public bundle digest mismatch.")
    _digest(export.get("private_index_digest"), "private index digest")
    if export.get("comparative_claim_permitted") is not False or export.get("provider_called") is not False:
        raise ValueError("Public export claims boundary is invalid.")
    if export.get("redaction_record") != _REDACTIONS:
        raise ValueError("Public redaction record is invalid.")
    runs = export.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("Public export runs are invalid.")
    expected_aggregate = _aggregate(runs)  # type: ignore[arg-type]
    if export.get("aggregate") != expected_aggregate:
        raise ValueError("Public aggregate does not match public run outcomes.")
    for run in runs:
        _validate_public_run(run)
    if export.get("price_source") is not None:
        PriceSource.from_dict(export["price_source"])
    _scan_public(unsigned)
    return {
        "schema_version": EXPORT_SCHEMA,
        "bundle_digest_verified": True,
        "runs_verified": len(runs),
        "completed_runs": expected_aggregate["completed_runs"],
        "aborted_runs": expected_aggregate["aborted_runs"],
        "provider_called": False,
    }
