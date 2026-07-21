from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from completion_verifier.adapters import canonical_json_sha256
from completion_verifier.sandbox.models import required_text


def _tuple_of_text(values: object, name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"'{name}' must be a tuple.")
    cleaned = tuple(required_text(value, name) for value in values)
    if not allow_empty and not cleaned:
        raise ValueError(f"'{name}' must contain at least one value.")
    if len(cleaned) != len(set(cleaned)):
        raise ValueError(f"'{name}' contains duplicate values.")
    return cleaned


def _digest(payload: dict[str, Any]) -> str:
    return canonical_json_sha256(payload)


@dataclass(frozen=True)
class StrategyPlan:
    contract_summary: str
    required_postcondition: str
    permitted_actions: tuple[str, ...]
    anticipated_failures: tuple[str, ...]
    retryable_failures: tuple[str, ...]
    terminal_failures: tuple[str, ...]
    stop_conditions: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract_summary", required_text(self.contract_summary, "contract_summary"))
        object.__setattr__(self, "required_postcondition", required_text(self.required_postcondition, "required_postcondition"))
        for name in (
            "permitted_actions",
            "anticipated_failures",
            "retryable_failures",
            "terminal_failures",
            "stop_conditions",
        ):
            object.__setattr__(self, name, _tuple_of_text(getattr(self, name), name))
        if self.permitted_actions != ("write_file",):
            raise ValueError("Strategist may permit only 'write_file'.")
        if not set(self.retryable_failures).issubset(self.anticipated_failures):
            raise ValueError("Retryable failures must be anticipated failures.")
        if set(self.retryable_failures) & set(self.terminal_failures):
            raise ValueError("Failure classes cannot be both retryable and terminal.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_summary": self.contract_summary,
            "required_postcondition": self.required_postcondition,
            "permitted_actions": list(self.permitted_actions),
            "anticipated_failures": list(self.anticipated_failures),
            "retryable_failures": list(self.retryable_failures),
            "terminal_failures": list(self.terminal_failures),
            "stop_conditions": list(self.stop_conditions),
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class OperatorRecord:
    approved_action: str
    attempted_path: str
    attempted_content_sha256: str
    attempt_number: int
    source_event_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "approved_action", required_text(self.approved_action, "approved_action"))
        object.__setattr__(self, "attempted_path", required_text(self.attempted_path, "attempted_path"))
        object.__setattr__(self, "attempted_content_sha256", required_text(self.attempted_content_sha256, "attempted_content_sha256"))
        object.__setattr__(self, "source_event_id", required_text(self.source_event_id, "source_event_id"))
        if self.approved_action != "write_file":
            raise ValueError("Operator may execute only 'write_file'.")
        if len(self.attempted_content_sha256) != 64:
            raise ValueError("Operator content digest must be a 64-character SHA-256 value.")
        if not isinstance(self.attempt_number, int) or isinstance(self.attempt_number, bool) or self.attempt_number not in {1, 2}:
            raise ValueError("Operator attempt_number must be 1 or 2.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved_action": self.approved_action,
            "attempted_path": self.attempted_path,
            "attempted_content_sha256": self.attempted_content_sha256,
            "attempt_number": self.attempt_number,
            "source_event_id": self.source_event_id,
        }


@dataclass(frozen=True)
class AuditRecord:
    decision: str
    source_assessment: str
    observation_assessment: str
    conflicts: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision", required_text(self.decision, "decision"))
        if self.decision not in {"accept", "recover", "fail"}:
            raise ValueError("Audit decision must be 'accept', 'recover', or 'fail'.")
        object.__setattr__(self, "source_assessment", required_text(self.source_assessment, "source_assessment"))
        object.__setattr__(self, "observation_assessment", required_text(self.observation_assessment, "observation_assessment"))
        object.__setattr__(self, "conflicts", _tuple_of_text(self.conflicts, "conflicts", allow_empty=True))
        object.__setattr__(self, "evidence_refs", _tuple_of_text(self.evidence_refs, "evidence_refs"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "source_assessment": self.source_assessment,
            "observation_assessment": self.observation_assessment,
            "conflicts": list(self.conflicts),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class RecoveryRecord:
    failure_class: str
    retry_justified: bool
    proposed_action: str | None
    remaining_attempts: int
    refusal_reason: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "failure_class", required_text(self.failure_class, "failure_class"))
        if not isinstance(self.retry_justified, bool):
            raise ValueError("'retry_justified' must be boolean.")
        if not isinstance(self.remaining_attempts, int) or isinstance(self.remaining_attempts, bool) or self.remaining_attempts not in {0, 1}:
            raise ValueError("'remaining_attempts' must be 0 or 1.")
        if self.retry_justified:
            if self.proposed_action != "write_file":
                raise ValueError("A justified recovery must propose 'write_file'.")
            if self.remaining_attempts != 1:
                raise ValueError("'remaining_attempts' must be 1 for a justified recovery.")
            if self.refusal_reason is not None:
                raise ValueError("A justified recovery cannot include a refusal reason.")
        else:
            if self.proposed_action is not None:
                raise ValueError("A refused recovery cannot propose an action.")
            if self.remaining_attempts != 0:
                raise ValueError("A refused recovery has zero remaining attempts.")
            object.__setattr__(self, "refusal_reason", required_text(self.refusal_reason, "refusal_reason"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_class": self.failure_class,
            "retry_justified": self.retry_justified,
            "proposed_action": self.proposed_action,
            "remaining_attempts": self.remaining_attempts,
            "refusal_reason": self.refusal_reason,
        }


@dataclass(frozen=True)
class SynthesisRecord:
    completion_claimed: bool
    verified_status: str
    summary: str
    limitations: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.completion_claimed, bool):
            raise ValueError("'completion_claimed' must be boolean.")
        object.__setattr__(self, "verified_status", required_text(self.verified_status, "verified_status"))
        if self.completion_claimed and self.verified_status != "VERIFIED_COMPLETE":
            raise ValueError("Synthesis cannot claim completion when the verifier is not VERIFIED_COMPLETE.")
        object.__setattr__(self, "summary", required_text(self.summary, "summary"))
        object.__setattr__(self, "limitations", _tuple_of_text(self.limitations, "limitations", allow_empty=True))
        object.__setattr__(self, "evidence_refs", _tuple_of_text(self.evidence_refs, "evidence_refs"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "completion_claimed": self.completion_claimed,
            "verified_status": self.verified_status,
            "summary": self.summary,
            "limitations": list(self.limitations),
            "evidence_refs": list(self.evidence_refs),
        }
