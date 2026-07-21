from __future__ import annotations

from ..models import ArenaRun


RETRYABLE_SCENARIOS = frozenset(
    {"false_success", "partial_write", "timeout_before_write", "rollback"}
)
TERMINAL_SECURITY_SCENARIOS = frozenset({"path_traversal", "symlink_escape"})


def assert_fair_pair(general: ArenaRun, specialist: ArenaRun) -> None:
    if general.condition != "general" or specialist.condition != "specialist":
        raise ValueError("A fair pair requires general and specialist conditions.")
    if general.scenario_id != specialist.scenario_id:
        raise ValueError("Fair pair scenario identifiers differ.")
    if general.config_digest != specialist.config_digest:
        raise ValueError("Fair pair configuration digests differ.")
    if general.contract_digest != specialist.contract_digest:
        raise ValueError("Fair pair contract digests differ.")
    if general.fairness_fingerprint != specialist.fairness_fingerprint:
        raise ValueError("Fair pair model, task, seed, tool, or attempt controls differ.")
