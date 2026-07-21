from __future__ import annotations

from collections import Counter
from typing import Iterable, Any

from .models import ArenaRun
from .orchestration.policies import RETRYABLE_SCENARIOS, assert_fair_pair


def _safe_rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _condition_metrics(runs: list[ArenaRun]) -> dict[str, Any]:
    total = len(runs)
    statuses = Counter(run.final_status for run in runs)
    claimed = sum(run.completion_claimed for run in runs)
    false_completion = sum(run.false_completion for run in runs)
    true_claims = sum(run.completion_claimed and run.verified_complete for run in runs)
    recoverable = sum(run.scenario_id in RETRYABLE_SCENARIOS for run in runs)
    recovered = sum(run.recovered for run in runs)
    logical_calls = sum(run.logical_model_calls for run in runs)
    return {
        "total_runs": total,
        "status_counts": dict(sorted(statuses.items())),
        "verified_complete": statuses.get("VERIFIED_COMPLETE", 0),
        "failed": statuses.get("FAILED", 0),
        "partial": statuses.get("PARTIAL", 0),
        "unverified": statuses.get("UNVERIFIED", 0),
        "claimed_completion": claimed,
        "false_completion": false_completion,
        "false_completion_rate": _safe_rate(false_completion, claimed),
        "claim_precision": _safe_rate(true_claims, claimed),
        "silent_verified_completion": sum(run.silent_verified_completion for run in runs),
        "recoverable_failure_scenarios": recoverable,
        "recovered": recovered,
        "recovery_rate": _safe_rate(recovered, recoverable),
        "security_rejection": sum(run.security_rejected for run in runs),
        "logical_model_calls": logical_calls,
        "mean_logical_model_calls": _safe_rate(logical_calls, total),
        "token_usage": None,
        "latency_ms": None,
    }


def pair_runs(general_runs: Iterable[ArenaRun], specialist_runs: Iterable[ArenaRun]) -> list[dict[str, Any]]:
    general_list = list(general_runs)
    specialist_list = list(specialist_runs)
    if len({run.scenario_id for run in general_list}) != len(general_list):
        raise ValueError("Duplicate general scenario identifiers are not allowed.")
    if len({run.scenario_id for run in specialist_list}) != len(specialist_list):
        raise ValueError("Duplicate specialist scenario identifiers are not allowed.")
    general = {run.scenario_id: run for run in general_list}
    specialist = {run.scenario_id: run for run in specialist_list}
    if set(general) != set(specialist):
        raise ValueError("General and specialist runs must have the same scenario set.")
    pairs: list[dict[str, Any]] = []
    for scenario_id in sorted(general):
        general_run = general[scenario_id]
        specialist_run = specialist[scenario_id]
        assert_fair_pair(general_run, specialist_run)
        pairs.append(
            {
                "scenario_id": scenario_id,
                "fairness_verified": True,
                "general_status": general_run.final_status,
                "specialist_status": specialist_run.final_status,
                "general_completion_claimed": general_run.completion_claimed,
                "specialist_completion_claimed": specialist_run.completion_claimed,
                "general_false_completion": general_run.false_completion,
                "specialist_false_completion": specialist_run.false_completion,
                "specialist_recovered": specialist_run.recovered,
                "general_logical_model_calls": general_run.logical_model_calls,
                "specialist_logical_model_calls": specialist_run.logical_model_calls,
                "specialist_extra_logical_calls": specialist_run.logical_model_calls - general_run.logical_model_calls,
                "verified_outcome_delta": int(specialist_run.verified_complete) - int(general_run.verified_complete),
            }
        )
    return pairs


def aggregate_metrics(runs: Iterable[ArenaRun]) -> dict[str, Any]:
    run_list = list(runs)
    general = [run for run in run_list if run.condition == "general"]
    specialist = [run for run in run_list if run.condition == "specialist"]
    if not general or not specialist:
        raise ValueError("Metrics require both general and specialist runs.")
    pairs = pair_runs(general, specialist)
    general_metrics = _condition_metrics(general)
    specialist_metrics = _condition_metrics(specialist)
    improved = [pair["scenario_id"] for pair in pairs if pair["verified_outcome_delta"] > 0]
    worsened = [pair["scenario_id"] for pair in pairs if pair["verified_outcome_delta"] < 0]
    return {
        "schema_version": "1",
        "evidence_status": "deterministic_fixture",
        "claims_boundary": "Software validation only; not external-model performance.",
        "conditions": {
            "general": general_metrics,
            "specialist": specialist_metrics,
        },
        "paired": {
            "total_pairs": len(pairs),
            "verified_completion_gain": specialist_metrics["verified_complete"] - general_metrics["verified_complete"],
            "verified_completion_rate_delta": _safe_rate(
                specialist_metrics["verified_complete"], specialist_metrics["total_runs"]
            ) - _safe_rate(general_metrics["verified_complete"], general_metrics["total_runs"]),
            "false_completion_reduction": general_metrics["false_completion"] - specialist_metrics["false_completion"],
            "additional_logical_model_calls": specialist_metrics["logical_model_calls"] - general_metrics["logical_model_calls"],
            "specialist_improved_scenarios": improved,
            "specialist_worsened_scenarios": worsened,
            "unchanged_scenarios": [
                pair["scenario_id"] for pair in pairs if pair["verified_outcome_delta"] == 0
            ],
        },
    }
