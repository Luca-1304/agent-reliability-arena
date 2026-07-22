from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import NormalDist, fmean, variance

from .live_requests import PromptCatalog
from .repeated_plan import RepeatedExperimentPlan
from .repeated_runner import verify_completed_trial
from .transports import verify_transport_ledger


_RECORD_FIELDS = {
    "trial_id",
    "general_verified_complete",
    "specialist_verified_complete",
    "logical_model_calls",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cached_input_tokens",
    "reasoning_tokens",
    "wall_clock_latency_ms",
    "provider_processing_ms",
    "provider_processing_reported_calls",
    "error_records",
}
_MEASUREMENT_FIELDS = (
    "logical_model_calls",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cached_input_tokens",
    "reasoning_tokens",
    "wall_clock_latency_ms",
    "provider_processing_ms",
    "provider_processing_reported_calls",
    "error_records",
)
_USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cached_input_tokens",
    "reasoning_tokens",
)
_Z_95 = NormalDist().inv_cdf(0.975)


def _non_negative_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"'{name}' must be a non-negative integer.")
    return value


def _read_object(path: Path, name: str) -> dict[str, object]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ValueError(f"{name} must be a regular non-symlink file.")
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{name} is not valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{name} must contain a JSON object.")
    return value


def wilson_interval(successes: int, total: int) -> dict[str, object]:
    successes = _non_negative_int(successes, "successes")
    total = _non_negative_int(total, "total")
    if total == 0 or successes > total:
        raise ValueError("Wilson interval requires 0 <= successes <= total and total > 0.")
    proportion = successes / total
    z_squared = _Z_95 * _Z_95
    denominator = 1.0 + z_squared / total
    centre = (proportion + z_squared / (2.0 * total)) / denominator
    half_width = (
        _Z_95
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z_squared / (4.0 * total * total)
        )
        / denominator
    )
    return {
        "method": "wilson-score-95-percent",
        "estimate": proportion,
        "lower": max(0.0, centre - half_width),
        "upper": min(1.0, centre + half_width),
        "successes": successes,
        "sample_size": total,
    }


def paired_normal_interval(differences: list[int]) -> dict[str, object]:
    if not isinstance(differences, list) or not differences:
        raise ValueError("Paired interval requires a non-empty list of trial differences.")
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value not in {-1, 0, 1}
        for value in differences
    ):
        raise ValueError("Paired trial differences must be integers in {-1, 0, 1}.")
    estimate = fmean(differences)
    if len(differences) == 1:
        standard_error = 0.0
        lower = upper = estimate
        limitation = "One paired trial provides no estimable between-trial variance."
    else:
        standard_error = math.sqrt(variance(differences) / len(differences))
        lower = max(-1.0, estimate - _Z_95 * standard_error)
        upper = min(1.0, estimate + _Z_95 * standard_error)
        limitation = (
            "This is a normal approximation over paired trial differences and may be unreliable "
            "for small, sparse or non-representative samples."
        )
    return {
        "method": "paired-normal-approximation-95-percent",
        "estimate": estimate,
        "lower": lower,
        "upper": upper,
        "standard_error": standard_error,
        "sample_size": len(differences),
        "limitation": limitation,
    }


def exact_sign_test_p_value(specialist_only: int, general_only: int) -> float | None:
    specialist_only = _non_negative_int(specialist_only, "specialist_only")
    general_only = _non_negative_int(general_only, "general_only")
    discordant = specialist_only + general_only
    if discordant == 0:
        return None
    smaller = min(specialist_only, general_only)
    one_tail = sum(math.comb(discordant, index) for index in range(smaller + 1)) / (2**discordant)
    return min(1.0, 2.0 * one_tail)


def _normalise_record(raw: object, index: int) -> dict[str, object]:
    if not isinstance(raw, dict) or set(raw) != _RECORD_FIELDS:
        raise ValueError(f"Trial analysis record {index} must contain exactly the documented fields.")
    trial_id = raw.get("trial_id")
    if not isinstance(trial_id, str) or not trial_id.strip():
        raise ValueError(f"Trial analysis record {index} has an invalid trial_id.")
    general = raw.get("general_verified_complete")
    specialist = raw.get("specialist_verified_complete")
    if not isinstance(general, bool) or not isinstance(specialist, bool):
        raise ValueError(f"Trial analysis record {index} has invalid paired outcomes.")
    result = dict(raw)
    result["trial_id"] = trial_id.strip()
    for field in _MEASUREMENT_FIELDS:
        result[field] = _non_negative_int(raw.get(field), f"record {index} {field}")
    return result


def analyse_trial_records(
    records: list[dict[str, object]],
    *,
    planned_trials: int,
    aborted_trials: int,
) -> dict[str, object]:
    if not isinstance(records, list) or not records:
        raise ValueError("Repeated experiment analysis requires at least one completed trial record.")
    normalised = [_normalise_record(raw, index) for index, raw in enumerate(records)]
    trial_ids = [str(record["trial_id"]) for record in normalised]
    if len(trial_ids) != len(set(trial_ids)):
        raise ValueError("Repeated experiment analysis trial_id values must be unique.")
    planned_trials = _non_negative_int(planned_trials, "planned_trials")
    aborted_trials = _non_negative_int(aborted_trials, "aborted_trials")
    completed_trials = len(normalised)
    if planned_trials < completed_trials + aborted_trials:
        raise ValueError("Planned trial count is below completed plus aborted trials.")

    general_count = sum(bool(record["general_verified_complete"]) for record in normalised)
    specialist_count = sum(bool(record["specialist_verified_complete"]) for record in normalised)
    both = sum(
        bool(record["general_verified_complete"]) and bool(record["specialist_verified_complete"])
        for record in normalised
    )
    neither = sum(
        not bool(record["general_verified_complete"]) and not bool(record["specialist_verified_complete"])
        for record in normalised
    )
    specialist_only = sum(
        not bool(record["general_verified_complete"]) and bool(record["specialist_verified_complete"])
        for record in normalised
    )
    general_only = sum(
        bool(record["general_verified_complete"]) and not bool(record["specialist_verified_complete"])
        for record in normalised
    )
    differences = [
        int(bool(record["specialist_verified_complete"]))
        - int(bool(record["general_verified_complete"]))
        for record in normalised
    ]
    measurements = {
        field: sum(int(record[field]) for record in normalised) for field in _MEASUREMENT_FIELDS
    }
    sign_p = exact_sign_test_p_value(specialist_only, general_only)

    return {
        "schema_version": "arena-repeated-experiment-analysis-v1",
        "trials": {
            "planned": planned_trials,
            "completed": completed_trials,
            "aborted": aborted_trials,
        },
        "outcomes": {
            "general_verified_complete": general_count,
            "specialist_verified_complete": specialist_count,
            "both_complete": both,
            "neither_complete": neither,
            "specialist_only": specialist_only,
            "general_only": general_only,
            "discordant_pairs": specialist_only + general_only,
        },
        "proportions": {
            "general": general_count / completed_trials,
            "specialist": specialist_count / completed_trials,
        },
        "paired_difference": fmean(differences),
        "uncertainty": {
            "general_completion": wilson_interval(general_count, completed_trials),
            "specialist_completion": wilson_interval(specialist_count, completed_trials),
            "paired_difference": paired_normal_interval(differences),
            "discordant_sign_test": {
                "method": "exact-two-sided-binomial-sign-test",
                "p_value": sign_p,
                "discordant_pairs": specialist_only + general_only,
                "limitation": (
                    "There are no discordant pairs, so no sign-test p-value is defined."
                    if sign_p is None
                    else "The sign test uses only discordant pairs and does not establish representativeness."
                ),
            },
        },
        "measurements": measurements,
        "comparative_claim_permitted": False,
        "limitations": [
            "Intervals describe only the recorded sample and its stated approximation.",
            "A p-value does not establish effect size, causality, representativeness or practical value.",
            "Provider, task, scenario, seed and stopping-rule choices constrain interpretation.",
            "Monetary cost is not inferred from token measurements without a separately dated price source.",
        ],
    }


def _ledger_measurements(path: Path) -> dict[str, int]:
    summary = verify_transport_ledger(path)
    totals = {field: 0 for field in _USAGE_FIELDS}
    latency = 0
    processing = 0
    processing_calls = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("outcome_type") != "result":
            continue
        result = row.get("result")
        if not isinstance(result, dict):
            raise ValueError("Verified ledger contains an invalid result record.")
        usage = result.get("usage")
        if not isinstance(usage, dict) or set(usage) != set(_USAGE_FIELDS):
            raise ValueError("Verified ledger contains an invalid usage record.")
        for field in _USAGE_FIELDS:
            totals[field] += _non_negative_int(usage.get(field), field)
        latency += _non_negative_int(result.get("latency_ms"), "latency_ms")
        provider_processing = result.get("provider_processing_ms")
        if provider_processing is not None:
            processing += _non_negative_int(provider_processing, "provider_processing_ms")
            processing_calls += 1
    return {
        "logical_model_calls": _non_negative_int(summary.get("records"), "ledger records"),
        **totals,
        "wall_clock_latency_ms": latency,
        "provider_processing_ms": processing,
        "provider_processing_reported_calls": processing_calls,
        "error_records": _non_negative_int(summary.get("errors"), "ledger errors"),
    }


def analyse_repeated_experiment(
    root: Path,
    plan: RepeatedExperimentPlan,
    catalog: PromptCatalog,
) -> dict[str, object]:
    if not isinstance(plan, RepeatedExperimentPlan):
        raise ValueError("'plan' must be a RepeatedExperimentPlan.")
    if not isinstance(catalog, PromptCatalog):
        raise ValueError("'catalog' must be a PromptCatalog.")
    experiment_root = Path(root)
    if experiment_root.is_symlink() or not experiment_root.is_dir():
        raise ValueError("Repeated experiment root must be a regular directory.")
    preflight = _read_object(experiment_root / "experiment-preflight.json", "experiment preflight")
    if preflight.get("plan_digest") != plan.digest:
        raise ValueError("Experiment preflight plan digest mismatch.")
    raw_trials = preflight.get("trials")
    if not isinstance(raw_trials, list):
        raise ValueError("Experiment preflight trials are invalid.")
    expected = {
        raw["trial_id"]: raw
        for raw in raw_trials
        if isinstance(raw, dict) and isinstance(raw.get("trial_id"), str)
    }
    if len(expected) != len(plan.trials):
        raise ValueError("Experiment preflight trial set does not match the plan.")

    completed_records: list[dict[str, object]] = []
    aborted_trials = 0
    for trial in plan.trials:
        trial_root = experiment_root / trial.trial_id
        if not trial_root.exists():
            break
        if (trial_root / "abort.json").exists():
            aborted_trials += 1
            break
        summary = verify_completed_trial(
            trial_root,
            trial,
            expected[trial.trial_id],
            plan,
            catalog,
        )
        conditions = summary["conditions"]
        measurements = _ledger_measurements(trial_root / "transport-calls.jsonl")
        completed_records.append(
            {
                "trial_id": trial.trial_id,
                "general_verified_complete": conditions["general"]["verified_complete"],
                "specialist_verified_complete": conditions["specialist"]["verified_complete"],
                **measurements,
            }
        )

    if not completed_records:
        raise ValueError("Repeated experiment contains no completed trial evidence to analyse.")
    if (experiment_root / "experiment-summary.json").exists():
        experiment_summary = _read_object(
            experiment_root / "experiment-summary.json",
            "experiment summary",
        )
        if experiment_summary.get("status") != "completed":
            raise ValueError("Experiment summary status is invalid.")
        if len(completed_records) != len(plan.trials):
            raise ValueError("Completed experiment summary conflicts with incomplete trial evidence.")
        aborted_trials = _non_negative_int(experiment_summary.get("aborted_trials"), "aborted_trials")
    elif (experiment_root / "experiment-abort.json").exists():
        experiment_abort = _read_object(experiment_root / "experiment-abort.json", "experiment abort")
        if experiment_abort.get("status") != "aborted":
            raise ValueError("Experiment abort status is invalid.")
        aborted_trials = max(1, aborted_trials)

    analysis = analyse_trial_records(
        completed_records,
        planned_trials=len(plan.trials),
        aborted_trials=aborted_trials,
    )
    analysis["plan_digest"] = plan.digest
    analysis["preflight_manifest_digest"] = preflight.get("manifest_digest")
    return analysis
