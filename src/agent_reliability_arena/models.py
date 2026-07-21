from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from completion_verifier.sandbox.models import SandboxRunResult


@dataclass(frozen=True)
class ArenaAttempt:
    attempt_number: int
    injected_scenario: str
    source_report: dict[str, Any]
    observation: dict[str, Any]
    evidence: dict[str, Any]
    status: str
    security_rejected: bool

    @classmethod
    def from_sandbox_result(
        cls,
        result: SandboxRunResult,
        attempt_number: int,
    ) -> "ArenaAttempt":
        return cls(
            attempt_number=attempt_number,
            injected_scenario=result.scenario_id,
            source_report=result.report.to_dict(),
            observation=result.observation.to_dict(),
            evidence=dict(result.case.events[0].evidence),
            status=result.evaluation.status.value,
            security_rejected=result.security_rejected,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_number": self.attempt_number,
            "injected_scenario": self.injected_scenario,
            "source_report": dict(self.source_report),
            "observation": dict(self.observation),
            "evidence": dict(self.evidence),
            "status": self.status,
            "security_rejected": self.security_rejected,
        }


@dataclass(frozen=True)
class ArenaRun:
    run_id: str
    condition: str
    scenario_id: str
    config_digest: str
    contract_digest: str
    fairness_fingerprint: dict[str, Any]
    attempts: tuple[ArenaAttempt, ...]
    final_status: str
    completion_claimed: bool
    logical_model_calls: int
    recovered: bool
    security_rejected: bool
    strategy: dict[str, Any] | None = None
    operator_records: tuple[dict[str, Any], ...] = ()
    audit_records: tuple[dict[str, Any], ...] = ()
    recovery: dict[str, Any] | None = None
    synthesis: dict[str, Any] | None = None

    @property
    def verified_complete(self) -> bool:
        return self.final_status == "VERIFIED_COMPLETE"

    @property
    def false_completion(self) -> bool:
        return self.completion_claimed and not self.verified_complete

    @property
    def silent_verified_completion(self) -> bool:
        return self.verified_complete and not self.completion_claimed

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "condition": self.condition,
            "scenario_id": self.scenario_id,
            "config_digest": self.config_digest,
            "contract_digest": self.contract_digest,
            "fairness_fingerprint": dict(self.fairness_fingerprint),
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "final_status": self.final_status,
            "completion_claimed": self.completion_claimed,
            "verified_complete": self.verified_complete,
            "false_completion": self.false_completion,
            "silent_verified_completion": self.silent_verified_completion,
            "logical_model_calls": self.logical_model_calls,
            "recovered": self.recovered,
            "security_rejected": self.security_rejected,
            "strategy": self.strategy,
            "operator_records": list(self.operator_records),
            "audit_records": list(self.audit_records),
            "recovery": self.recovery,
            "synthesis": self.synthesis,
        }
