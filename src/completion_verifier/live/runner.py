from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..evaluator import evaluate_case
from ..sandbox.filesystem import SafeFileSandbox, SandboxSecurityError
from ..sandbox.models import SourceToolReport
from ..sandbox.runner import build_postcondition_case
from .models import (
    FunctionCallRecord,
    LiveRunConfig,
    LiveRunResult,
    ResponseRecord,
    ResponseRequest,
    ToolOutputRecord,
    contract_instructions,
    redact_error_text,
    write_file_tool,
)
from .transport import ResponsesTransport
from .runner_support import LiveRunnerHelpers


class LiveResponsesRunner(LiveRunnerHelpers):
    name = "responses-sandbox-runner"
    version = "1"

    def run(
        self,
        config: LiveRunConfig,
        transport: ResponsesTransport,
        sandbox_root: Path,
    ) -> LiveRunResult:
        sandbox = SafeFileSandbox(Path(sandbox_root))
        requests: list[ResponseRequest] = []
        responses: list[ResponseRecord] = []
        function_calls: list[FunctionCallRecord] = []
        tool_outputs: list[ToolOutputRecord] = []
        errors: list[dict[str, Any]] = []
        seen_call_ids: set[str] = set()
        first_request = ResponseRequest.first(config)
        input_items: list[dict[str, Any]] = [
            dict(item) for item in first_request.input_items
        ]
        executed = False
        attempted_path = config.contract.path
        halted = False

        for round_index in range(config.max_tool_rounds):
            if round_index == 0:
                request = first_request
            else:
                request = self._tool_request(config, tuple(input_items))
            record = self._create(transport, request, len(requests))
            requests.append(request)
            responses.append(record)
            input_items.extend(dict(item) for item in record.output_items)

            if record.transport_error is not None:
                errors.append(
                    self._error(
                        "transport_error",
                        record.transport_error.get("message", "Transport failed."),
                        record.request_index,
                    )
                )
                halted = True
                break
            if record.status != "completed":
                errors.append(
                    self._error(
                        "incomplete_response",
                        f"Response status was '{record.status}'.",
                        record.request_index,
                    )
                )
                halted = True
                break

            calls = [
                item for item in record.output_items
                if item.get("type") == "function_call"
            ]
            if not calls:
                errors.append(
                    self._error(
                        "missing_function_call",
                        "A required tool round returned no function call.",
                        record.request_index,
                    )
                )
                break
            if len(calls) > 1:
                errors.append(
                    self._error(
                        "multiple_function_calls",
                        "Only one function call is permitted per round.",
                        record.request_index,
                    )
                )
                for item in calls:
                    call = self._record_rejected_call(
                        item,
                        record.request_index,
                        "multiple_function_calls",
                    )
                    function_calls.append(call)
                    output = self._tool_error_output(call, "multiple_function_calls")
                    if output is not None:
                        tool_outputs.append(output)
                        input_items.append(output.input_item())
                continue

            item = calls[0]
            call, parsed, code = self._validate_call(
                item,
                record.request_index,
                config,
                seen_call_ids,
            )
            function_calls.append(call)
            if parsed is not None:
                attempted_path = str(parsed.get("path", attempted_path))
            if code is not None:
                errors.append(
                    self._error(code, call.validation_error or code, record.request_index)
                )
                output = self._tool_error_output(call, code)
                if output is not None:
                    tool_outputs.append(output)
                    input_items.append(output.input_item())
                continue

            try:
                sandbox.write_text(config.contract.path, config.contract.content)
            except (OSError, ValueError, SandboxSecurityError) as exc:
                code = "sandbox_write_error"
                errors.append(self._error(code, redact_error_text(exc), record.request_index))
                output = ToolOutputRecord(
                    request_index=record.request_index,
                    call_id=call.call_id or "invalid-call",
                    executed=False,
                    output={"ok": False, "error": code},
                )
                tool_outputs.append(output)
                input_items.append(output.input_item())
                continue

            executed = True
            output = ToolOutputRecord(
                request_index=record.request_index,
                call_id=call.call_id or "invalid-call",
                executed=True,
                output={
                    "ok": True,
                    "path": config.contract.path,
                    "bytes_written": config.contract.expected_size,
                },
            )
            tool_outputs.append(output)
            input_items.append(output.input_item())
            break

        completion_claimed = False
        final_summary: str | None = None
        if not halted:
            final_request = self._final_request(config, tuple(input_items))
            final_record = self._create(
                transport,
                final_request,
                len(requests),
            )
            requests.append(final_request)
            responses.append(final_record)
            if final_record.transport_error is not None:
                errors.append(
                    self._error(
                        "transport_error",
                        final_record.transport_error.get("message", "Transport failed."),
                        final_record.request_index,
                    )
                )
            elif final_record.status != "completed":
                errors.append(
                    self._error(
                        "incomplete_response",
                        f"Final response status was '{final_record.status}'.",
                        final_record.request_index,
                    )
                )
            elif any(
                item.get("type") == "function_call"
                for item in final_record.output_items
            ):
                errors.append(
                    self._error(
                        "function_call_in_final_response",
                        "The final response returned a function call after tools were disabled.",
                        final_record.request_index,
                    )
                )
            else:
                completion_claimed, final_summary, claim_error = self._parse_final_claim(
                    self._extract_output_text(final_record)
                )
                if claim_error is not None:
                    errors.append(
                        self._error(
                            claim_error,
                            "Final response did not match the required claim schema.",
                            final_record.request_index,
                        )
                    )

        observation = sandbox.observe(config.contract)
        source_report = SourceToolReport(
            scenario_id="live-run",
            attempted_path=attempted_path,
            reported_success=executed,
            reported_evidence=(
                dict(tool_outputs[-1].output) if tool_outputs else {}
            ),
            completion_claimed=completion_claimed,
            source_event_id=(
                function_calls[-1].call_id
                if function_calls and function_calls[-1].call_id
                else "live-no-call"
            ),
            error_kind=(str(errors[-1]["code"]) if errors else None),
        )
        case = build_postcondition_case(
            contract=config.contract,
            observation=observation,
            completion_claimed=completion_claimed,
            case_id=f"{config.run_id}--postcondition",
            task=config.task,
        )
        evaluation = evaluate_case(case)
        return LiveRunResult(
            config=config,
            requests=tuple(requests),
            responses=tuple(responses),
            function_calls=tuple(function_calls),
            tool_outputs=tuple(tool_outputs),
            source_report=source_report,
            observation=observation,
            case=case,
            evaluation=evaluation,
            completion_claimed=completion_claimed,
            final_summary=final_summary,
            usage=self._aggregate_usage(responses),
            errors=tuple(errors),
            transport_name=str(getattr(transport, "name", type(transport).__name__)),
            transport_version=str(getattr(transport, "version", "unknown")),
        )

