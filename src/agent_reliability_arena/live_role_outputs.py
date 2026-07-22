from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from .schemas import AuditRecord, RecoveryRecord, StrategyPlan, SynthesisRecord
from .transports.base import canonical_json_sha256

MAX_ROLE_OUTPUT_BYTES = 65_536
ROLE_NAMES = (
    "general",
    "strategist",
    "operator",
    "auditor",
    "recovery",
    "synthesiser",
)

_GENERAL_FIELDS = {"action", "path", "content", "completion_claimed", "rationale"}
_STRATEGY_FIELDS = {
    "contract_summary",
    "required_postcondition",
    "permitted_actions",
    "anticipated_failures",
    "retryable_failures",
    "terminal_failures",
    "stop_conditions",
}
_OPERATOR_FIELDS = {"approved_action", "path", "content", "attempt_number", "rationale"}
_AUDIT_FIELDS = {
    "decision",
    "source_assessment",
    "observation_assessment",
    "conflicts",
    "evidence_refs",
}
_RECOVERY_FIELDS = {
    "failure_class",
    "retry_justified",
    "proposed_action",
    "remaining_attempts",
    "refusal_reason",
}
_SYNTHESIS_FIELDS = {
    "completion_claimed",
    "verified_status",
    "summary",
    "limitations",
    "evidence_refs",
}


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{name}' must be a non-empty string.")
    return value


def _string_or_none(value: object, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"'{name}' must be a string or null.")
    return value


def _boolean(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"'{name}' must be boolean.")
    return value


def _attempt_number(value: object, name: str = "attempt_number") -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value not in {1, 2}:
        raise ValueError(f"'{name}' must be 1 or 2.")
    return value


def _exact_fields(payload: dict[str, Any], expected: set[str], role: str) -> None:
    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if unknown:
            details.append("unknown=" + ",".join(unknown))
        raise ValueError(f"Invalid fields for role '{role}': " + "; ".join(details))


def _text_list(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"'{name}' must be a JSON array.")
    cleaned = tuple(_required_text(item, name) for item in value)
    if len(cleaned) != len(set(cleaned)):
        raise ValueError(f"'{name}' contains duplicate values.")
    return cleaned


def _safe_relative_path(value: object, name: str = "path") -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"'{name}' must be a non-empty safe relative path.")
    if "\x00" in value or "\\" in value:
        raise ValueError(f"'{name}' must be a safe relative POSIX path.")
    if value.startswith("/") or value.endswith("/"):
        raise ValueError(f"'{name}' must be a safe relative POSIX path.")
    if len(value) >= 2 and value[1] == ":":
        raise ValueError(f"'{name}' must not be a drive-qualified path.")
    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError(f"'{name}' must not contain empty, dot, or traversal segments.")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ValueError(f"'{name}' must be a normalised safe relative POSIX path.")
    return value


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key '{key}' is not allowed.")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON number '{value}' is not allowed.")


def _strict_json_object(output_text: object) -> tuple[str, bytes, dict[str, Any]]:
    if not isinstance(output_text, str) or not output_text:
        raise ValueError("'output_text' must be a non-empty string.")
    try:
        encoded = output_text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("'output_text' must be valid UTF-8 text.") from exc
    if len(encoded) > MAX_ROLE_OUTPUT_BYTES:
        raise ValueError("Role output exceeds the 65,536-byte limit.")
    try:
        payload = json.loads(
            output_text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Role output must be exactly one valid JSON object.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Role output must have one top-level JSON object.")
    return output_text, encoded, payload


@dataclass(frozen=True)
class GeneralProposal:
    action: str
    path: str | None
    content: str | None
    completion_claimed: bool
    rationale: str

    def __post_init__(self) -> None:
        action = _required_text(self.action, "action").strip()
        if action not in {"write_file", "none"}:
            raise ValueError("'action' must be 'write_file' or 'none'.")
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "completion_claimed", _boolean(self.completion_claimed, "completion_claimed"))
        object.__setattr__(self, "rationale", _required_text(self.rationale, "rationale"))
        if action == "write_file":
            object.__setattr__(self, "path", _safe_relative_path(self.path))
            if not isinstance(self.content, str):
                raise ValueError("A write_file proposal requires string 'content'.")
        else:
            if self.path is not None or self.content is not None:
                raise ValueError("A none proposal requires null path and content.")

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "path": self.path,
            "content": self.content,
            "completion_claimed": self.completion_claimed,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class OperatorProposal:
    approved_action: str
    path: str
    content: str
    attempt_number: int
    rationale: str

    def __post_init__(self) -> None:
        action = _required_text(self.approved_action, "approved_action").strip()
        if action != "write_file":
            raise ValueError("Operator approved_action must be 'write_file'.")
        object.__setattr__(self, "approved_action", action)
        object.__setattr__(self, "path", _safe_relative_path(self.path))
        if not isinstance(self.content, str):
            raise ValueError("Operator 'content' must be a string.")
        object.__setattr__(self, "attempt_number", _attempt_number(self.attempt_number))
        object.__setattr__(self, "rationale", _required_text(self.rationale, "rationale"))

    def to_dict(self) -> dict[str, object]:
        return {
            "approved_action": self.approved_action,
            "path": self.path,
            "content": self.content,
            "attempt_number": self.attempt_number,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class ParsedRoleOutput:
    role: str
    value: GeneralProposal | StrategyPlan | OperatorProposal | AuditRecord | RecoveryRecord | SynthesisRecord
    payload: dict[str, object]
    raw_sha256: str
    canonical_sha256: str

    def __post_init__(self) -> None:
        if self.role not in ROLE_NAMES:
            raise ValueError(f"Unknown role '{self.role}'.")
        if not isinstance(self.payload, dict):
            raise ValueError("'payload' must be a dictionary.")
        for name in ("raw_sha256", "canonical_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64:
                raise ValueError(f"'{name}' must be a 64-character SHA-256 value.")


def _parse_general(payload: dict[str, Any]) -> GeneralProposal:
    _exact_fields(payload, _GENERAL_FIELDS, "general")
    return GeneralProposal(
        action=payload["action"],
        path=_string_or_none(payload["path"], "path"),
        content=_string_or_none(payload["content"], "content"),
        completion_claimed=payload["completion_claimed"],
        rationale=payload["rationale"],
    )


def _parse_strategy(payload: dict[str, Any]) -> StrategyPlan:
    _exact_fields(payload, _STRATEGY_FIELDS, "strategist")
    return StrategyPlan(
        contract_summary=payload["contract_summary"],
        required_postcondition=payload["required_postcondition"],
        permitted_actions=_text_list(payload["permitted_actions"], "permitted_actions"),
        anticipated_failures=_text_list(payload["anticipated_failures"], "anticipated_failures"),
        retryable_failures=_text_list(payload["retryable_failures"], "retryable_failures"),
        terminal_failures=_text_list(payload["terminal_failures"], "terminal_failures"),
        stop_conditions=_text_list(payload["stop_conditions"], "stop_conditions"),
    )


def _parse_operator(payload: dict[str, Any], expected_attempt_number: int | None) -> OperatorProposal:
    _exact_fields(payload, _OPERATOR_FIELDS, "operator")
    proposal = OperatorProposal(
        approved_action=payload["approved_action"],
        path=payload["path"],
        content=payload["content"],
        attempt_number=payload["attempt_number"],
        rationale=payload["rationale"],
    )
    if expected_attempt_number is not None:
        expected = _attempt_number(expected_attempt_number, "expected_attempt_number")
        if proposal.attempt_number != expected:
            raise ValueError(
                "Operator attempt_number does not match expected_attempt_number."
            )
    return proposal


def _parse_audit(payload: dict[str, Any]) -> AuditRecord:
    _exact_fields(payload, _AUDIT_FIELDS, "auditor")
    return AuditRecord(
        decision=payload["decision"],
        source_assessment=payload["source_assessment"],
        observation_assessment=payload["observation_assessment"],
        conflicts=_text_list(payload["conflicts"], "conflicts"),
        evidence_refs=_text_list(payload["evidence_refs"], "evidence_refs"),
    )


def _parse_recovery(payload: dict[str, Any]) -> RecoveryRecord:
    _exact_fields(payload, _RECOVERY_FIELDS, "recovery")
    return RecoveryRecord(
        failure_class=payload["failure_class"],
        retry_justified=payload["retry_justified"],
        proposed_action=payload["proposed_action"],
        remaining_attempts=payload["remaining_attempts"],
        refusal_reason=payload["refusal_reason"],
    )


def _parse_synthesis(payload: dict[str, Any]) -> SynthesisRecord:
    _exact_fields(payload, _SYNTHESIS_FIELDS, "synthesiser")
    return SynthesisRecord(
        completion_claimed=payload["completion_claimed"],
        verified_status=payload["verified_status"],
        summary=payload["summary"],
        limitations=_text_list(payload["limitations"], "limitations"),
        evidence_refs=_text_list(payload["evidence_refs"], "evidence_refs"),
    )


def parse_live_role_output(
    role: str,
    output_text: str,
    *,
    expected_attempt_number: int | None = None,
) -> ParsedRoleOutput:
    if not isinstance(role, str) or role not in ROLE_NAMES:
        raise ValueError(f"Unknown role '{role}'.")
    if expected_attempt_number is not None and role != "operator":
        raise ValueError("expected_attempt_number is valid only for operator output.")
    raw_text, encoded, payload = _strict_json_object(output_text)
    if role == "general":
        value = _parse_general(payload)
    elif role == "strategist":
        value = _parse_strategy(payload)
    elif role == "operator":
        value = _parse_operator(payload, expected_attempt_number)
    elif role == "auditor":
        value = _parse_audit(payload)
    elif role == "recovery":
        value = _parse_recovery(payload)
    else:
        value = _parse_synthesis(payload)
    canonical_payload = value.to_dict()
    return ParsedRoleOutput(
        role=role,
        value=value,
        payload=canonical_payload,
        raw_sha256=hashlib.sha256(encoded).hexdigest(),
        canonical_sha256=canonical_json_sha256(canonical_payload),
    )
