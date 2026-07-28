from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from completion_verifier.evaluator import evaluate_case
from completion_verifier.models import Case


class PortfolioDemoError(ValueError):
    """Raised when the public portfolio input is malformed or inconsistent."""


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PortfolioDemoError(f"Unable to read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PortfolioDemoError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise PortfolioDemoError(f"{path} must contain a JSON object.")
    return raw


def _requirements(contract: dict[str, Any]) -> list[dict[str, object]]:
    raw_requirements = contract.get("requirements")
    if not isinstance(raw_requirements, list) or not raw_requirements:
        raise PortfolioDemoError("Contract requires a non-empty requirements list.")

    requirements: list[dict[str, object]] = []
    seen_actions: set[str] = set()
    for raw in raw_requirements:
        if not isinstance(raw, dict):
            raise PortfolioDemoError("Each contract requirement must be an object.")
        action = str(raw.get("action", "")).strip()
        evidence_fields = raw.get("required_evidence")
        if not action:
            raise PortfolioDemoError("Each contract requirement requires an action.")
        if action in seen_actions:
            raise PortfolioDemoError(f"Duplicate contract action: {action}")
        if not isinstance(evidence_fields, list) or not evidence_fields or not all(
            isinstance(field, str) and field.strip() for field in evidence_fields
        ):
            raise PortfolioDemoError(
                f"Requirement {action!r} requires a non-empty required_evidence list."
            )
        seen_actions.add(action)
        requirements.append(
            {
                "action": action,
                "evidence_fields": [field.strip() for field in evidence_fields],
            }
        )
    return requirements


def _require_events(raw_events: object) -> list[dict[str, Any]]:
    if not isinstance(raw_events, list):
        raise PortfolioDemoError("Scenario events must be a list.")
    events: list[dict[str, Any]] = []
    for raw in raw_events:
        if not isinstance(raw, dict):
            raise PortfolioDemoError("Each scenario event must be an object.")
        action = str(raw.get("action", "")).strip()
        success = raw.get("success")
        evidence = raw.get("evidence", {})
        if not action or not isinstance(success, bool) or not isinstance(evidence, dict):
            raise PortfolioDemoError(
                "Each event requires a non-empty action, boolean success and object evidence."
            )
        events.append(
            {
                "action": action,
                "success": success,
                "evidence": deepcopy(evidence),
            }
        )
    return events


def _mark_failed(event: dict[str, Any], reason: str) -> None:
    event["success"] = False
    evidence = event.setdefault("evidence", {})
    assert isinstance(evidence, dict)
    mismatches = evidence.setdefault("contract_mismatches", [])
    if not isinstance(mismatches, list):
        mismatches = [str(mismatches)]
        evidence["contract_mismatches"] = mismatches
    if reason not in mismatches:
        mismatches.append(reason)


def _latest_event(
    events: list[dict[str, Any]], action: str, *, successful_only: bool = False
) -> tuple[int, dict[str, Any]] | None:
    for index in range(len(events) - 1, -1, -1):
        event = events[index]
        if event["action"] != action:
            continue
        if successful_only and not event["success"]:
            continue
        return index, event
    return None


def _enforce_expected_values(
    contract: dict[str, Any], events: list[dict[str, Any]]
) -> None:
    raw_requirements = contract["requirements"]
    assert isinstance(raw_requirements, list)
    expected_by_action: dict[str, dict[str, Any]] = {}
    for raw in raw_requirements:
        assert isinstance(raw, dict)
        expected = raw.get("expected_values", {})
        if expected is None:
            expected = {}
        if not isinstance(expected, dict):
            raise PortfolioDemoError("expected_values must be an object when present.")
        expected_by_action[str(raw["action"])] = expected

    for event in events:
        expected = expected_by_action.get(str(event["action"]), {})
        evidence = event["evidence"]
        assert isinstance(evidence, dict)
        for field, required_value in expected.items():
            if evidence.get(field) != required_value:
                _mark_failed(
                    event,
                    f"expected {field}={required_value!r}, observed {evidence.get(field)!r}",
                )


def _enforce_cross_event_contract(events: list[dict[str, Any]]) -> None:
    approval = _latest_event(
        events, "approve_customer_information_request", successful_only=True
    )
    created = _latest_event(events, "create_email_draft", successful_only=True)

    if approval is not None and created is not None:
        _, approval_event = approval
        _, created_event = created
        approval_evidence = approval_event["evidence"]
        created_evidence = created_event["evidence"]
        assert isinstance(approval_evidence, dict)
        assert isinstance(created_evidence, dict)
        if approval_evidence.get("content_sha256") != created_evidence.get(
            "content_sha256"
        ):
            _mark_failed(created_event, "created content does not match approved content")

    successful_creates: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, event in enumerate(events):
        if event["action"] != "create_email_draft" or not event["success"]:
            continue
        evidence = event["evidence"]
        assert isinstance(evidence, dict)
        key = evidence.get("idempotency_key")
        if isinstance(key, str) and key:
            successful_creates.setdefault(key, []).append((index, event))
    for key, matches in successful_creates.items():
        if len(matches) > 1:
            _, latest = matches[-1]
            _mark_failed(latest, f"duplicate successful mutation for idempotency key {key}")

    latest_created = _latest_event(events, "create_email_draft", successful_only=True)
    observed = _latest_event(events, "observe_email_draft", successful_only=True)
    if latest_created is not None and observed is not None:
        _, created_event = latest_created
        _, observed_event = observed
        created_evidence = created_event["evidence"]
        observed_evidence = observed_event["evidence"]
        assert isinstance(created_evidence, dict)
        assert isinstance(observed_evidence, dict)
        if created_evidence.get("draft_id") != observed_evidence.get(
            "observed_draft_id"
        ):
            _mark_failed(observed_event, "observer read a different draft identifier")
        if created_evidence.get("content_sha256") != observed_evidence.get(
            "observed_content_sha256"
        ):
            _mark_failed(observed_event, "observer read different draft content")

    audit = _latest_event(events, "write_audit_record", successful_only=True)
    if audit is not None:
        index, audit_event = audit
        evidence = audit_event["evidence"]
        assert isinstance(evidence, dict)
        if evidence.get("event_count") != index:
            _mark_failed(
                audit_event,
                f"audit event_count must equal preceding event count {index}",
            )


def canonicalise_events(
    contract: dict[str, Any], raw_events: object
) -> list[dict[str, Any]]:
    events = _require_events(raw_events)
    _enforce_expected_values(contract, events)
    _enforce_cross_event_contract(events)
    return events


def evaluate_portfolio_scenario(
    contract: dict[str, Any], scenario: dict[str, Any]
) -> dict[str, Any]:
    scenario_id = str(scenario.get("scenario_id", "")).strip()
    completion_claimed = scenario.get("completion_claimed")
    expected_status = str(scenario.get("expected_status", "")).strip()
    if not scenario_id:
        raise PortfolioDemoError("Each scenario requires scenario_id.")
    if not isinstance(completion_claimed, bool):
        raise PortfolioDemoError(
            f"Scenario {scenario_id!r} requires boolean completion_claimed."
        )
    if not expected_status:
        raise PortfolioDemoError(f"Scenario {scenario_id!r} requires expected_status.")

    events = canonicalise_events(contract, scenario.get("events"))
    case = Case.from_dict(
        {
            "case_id": scenario_id,
            "task": str(contract.get("completion_definition", "")).strip()
            or "Satisfy the public AI Operations Assurance contract.",
            "completion_claimed": completion_claimed,
            "requirements": _requirements(contract),
            "events": events,
        }
    )
    evaluation = evaluate_case(case)
    false_completion = completion_claimed and evaluation.status.value != "VERIFIED_COMPLETE"
    silent_verified_completion = (
        not completion_claimed and evaluation.status.value == "VERIFIED_COMPLETE"
    )
    return {
        "scenario_id": scenario_id,
        "expected_status": expected_status,
        "evaluation": evaluation.to_dict(),
        "matches_expected": evaluation.status.value == expected_status,
        "false_completion": false_completion,
        "silent_verified_completion": silent_verified_completion,
        "canonical_events": events,
    }


def evaluate_portfolio_suite(
    contract: dict[str, Any], suite: dict[str, Any]
) -> dict[str, Any]:
    raw_scenarios = suite.get("scenarios")
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        raise PortfolioDemoError("Scenario suite requires a non-empty scenarios list.")
    results = []
    for raw in raw_scenarios:
        if not isinstance(raw, dict):
            raise PortfolioDemoError("Each scenario must be an object.")
        results.append(evaluate_portfolio_scenario(contract, raw))
    return {
        "contract_id": contract.get("contract_id"),
        "scenario_count": len(results),
        "all_expected": all(result["matches_expected"] for result in results),
        "verified_complete": sum(
            result["evaluation"]["status"] == "VERIFIED_COMPLETE"
            for result in results
        ),
        "false_completions": sum(result["false_completion"] for result in results),
        "results": results,
    }


def _default_portfolio_root() -> Path:
    return Path(__file__).resolve().parents[2] / "portfolio" / "ai-operations-assurance"


def build_parser() -> argparse.ArgumentParser:
    root = _default_portfolio_root()
    parser = argparse.ArgumentParser(
        description="Run the public AI Operations Assurance evidence-contract demo."
    )
    parser.add_argument(
        "--contract", type=Path, default=root / "acceptance_contract.json"
    )
    parser.add_argument("--scenarios", type=Path, default=root / "scenarios.json")
    parser.add_argument("--json", action="store_true", help="Print full JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        contract = load_json_object(args.contract)
        suite = load_json_object(args.scenarios)
        report = evaluate_portfolio_suite(contract, suite)
    except PortfolioDemoError as exc:
        print(f"portfolio demo error: {exc}")
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        for result in report["results"]:
            evaluation = result["evaluation"]
            marker = "PASS" if result["matches_expected"] else "MISMATCH"
            print(
                f"{result['scenario_id']:<36} "
                f"{evaluation['status']:<18} expected={result['expected_status']:<18} {marker}"
            )
        print(
            f"scenarios={report['scenario_count']} "
            f"verified={report['verified_complete']} "
            f"false_completions={report['false_completions']} "
            f"all_expected={str(report['all_expected']).lower()}"
        )
    return 0 if report["all_expected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
