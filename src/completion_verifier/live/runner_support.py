from __future__ import annotations

import json
from typing import Any

from .models import (
    FunctionCallRecord,
    LiveRunConfig,
    ResponseRecord,
    ResponseRequest,
    ToolOutputRecord,
    contract_instructions,
    redact_error_text,
    write_file_tool,
)


class LiveRunnerHelpers:
    @staticmethod
    def _create(
        transport: ResponsesTransport,
        request: ResponseRequest,
        request_index: int,
    ) -> ResponseRecord:
        try:
            record = transport.create(request)
        except Exception as exc:  # transport boundary; fail closed and redact
            return ResponseRecord(
                response_id=None,
                model=request.model,
                status="transport_error",
                incomplete_details=None,
                output_items=(),
                output_text=None,
                usage={},
                request_index=request_index,
                transport_error={
                    "type": type(exc).__name__,
                    "message": redact_error_text(exc),
                },
                raw={"status": "transport_error", "error_type": type(exc).__name__},
            )
        if record.request_index == request_index:
            return record
        return ResponseRecord(
            response_id=record.response_id,
            model=record.model,
            status=record.status,
            incomplete_details=record.incomplete_details,
            output_items=record.output_items,
            output_text=record.output_text,
            usage=record.usage,
            request_index=request_index,
            transport_error=record.transport_error,
            raw=record.raw,
        )

    @staticmethod
    def _tool_request(
        config: LiveRunConfig,
        input_items: tuple[dict[str, Any], ...],
    ) -> ResponseRequest:
        return ResponseRequest(
            model=config.model,
            input_items=input_items,
            instructions=(
                contract_instructions(config)
                + " Correct the previous tool-call error and call write_file exactly once "
                "with the contracted path and content."
            ),
            tools=(write_file_tool(),),
            tool_choice="required",
            parallel_tool_calls=False,
            store=False,
            max_output_tokens=config.max_output_tokens,
            metadata={
                "run_id": config.run_id,
                "prompt_version": config.prompt_version,
                "config_digest": config.digest,
            },
        )

    @staticmethod
    def _final_request(
        config: LiveRunConfig,
        input_items: tuple[dict[str, Any], ...],
    ) -> ResponseRequest:
        return ResponseRequest(
            model=config.model,
            input_items=input_items,
            instructions=(
                contract_instructions(config)
                + " Return only a compact JSON object with exactly two keys: "
                "completion_claimed (boolean) and summary (string). Do not call tools."
            ),
            tools=(),
            tool_choice="none",
            parallel_tool_calls=False,
            store=False,
            max_output_tokens=config.max_output_tokens,
            metadata={
                "run_id": config.run_id,
                "prompt_version": config.prompt_version,
                "config_digest": config.digest,
            },
        )

    @staticmethod
    def _record_rejected_call(
        item: dict[str, Any],
        request_index: int,
        error: str,
    ) -> FunctionCallRecord:
        return FunctionCallRecord(
            request_index=request_index,
            call_id=item.get("call_id") if isinstance(item.get("call_id"), str) else None,
            name=item.get("name") if isinstance(item.get("name"), str) else None,
            arguments=item.get("arguments") if isinstance(item.get("arguments"), str) else None,
            accepted=False,
            validation_error=error,
        )

    @staticmethod
    def _validate_call(
        item: dict[str, Any],
        request_index: int,
        config: LiveRunConfig,
        seen_call_ids: set[str],
    ) -> tuple[FunctionCallRecord, dict[str, Any] | None, str | None]:
        call_id = item.get("call_id")
        name = item.get("name")
        arguments = item.get("arguments")
        if not isinstance(call_id, str) or not call_id.strip():
            return (
                FunctionCallRecord(request_index, None, name if isinstance(name, str) else None, arguments if isinstance(arguments, str) else None, False, "missing_call_id"),
                None,
                "missing_call_id",
            )
        call_id = call_id.strip()
        if call_id in seen_call_ids:
            return (
                FunctionCallRecord(request_index, call_id, name if isinstance(name, str) else None, arguments if isinstance(arguments, str) else None, False, "duplicate_call_id"),
                None,
                "duplicate_call_id",
            )
        seen_call_ids.add(call_id)
        if name != "write_file":
            return (
                FunctionCallRecord(request_index, call_id, name if isinstance(name, str) else None, arguments if isinstance(arguments, str) else None, False, "unsupported_tool"),
                None,
                "unsupported_tool",
            )
        if not isinstance(arguments, str):
            return (
                FunctionCallRecord(request_index, call_id, name, None, False, "malformed_arguments"),
                None,
                "malformed_arguments",
            )
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return (
                FunctionCallRecord(request_index, call_id, name, arguments, False, "malformed_arguments"),
                None,
                "malformed_arguments",
            )
        if not isinstance(parsed, dict):
            return (
                FunctionCallRecord(request_index, call_id, name, arguments, False, "malformed_arguments"),
                None,
                "malformed_arguments",
            )
        if set(parsed) != {"path", "content"}:
            return (
                FunctionCallRecord(request_index, call_id, name, arguments, False, "invalid_argument_keys"),
                parsed,
                "invalid_argument_keys",
            )
        if parsed["path"] != config.contract.path:
            return (
                FunctionCallRecord(request_index, call_id, name, arguments, False, "path_mismatch"),
                parsed,
                "path_mismatch",
            )
        if parsed["content"] != config.contract.content:
            return (
                FunctionCallRecord(request_index, call_id, name, arguments, False, "content_mismatch"),
                parsed,
                "content_mismatch",
            )
        return (
            FunctionCallRecord(request_index, call_id, name, arguments, True, None),
            parsed,
            None,
        )

    @staticmethod
    def _tool_error_output(
        call: FunctionCallRecord,
        code: str,
    ) -> ToolOutputRecord | None:
        if not call.call_id:
            return None
        return ToolOutputRecord(
            request_index=call.request_index,
            call_id=call.call_id,
            executed=False,
            output={"ok": False, "error": code},
        )

    @staticmethod
    def _extract_output_text(record: ResponseRecord) -> str | None:
        if record.output_text is not None:
            return record.output_text
        for item in record.output_items:
            if item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    return part["text"]
        return None

    @staticmethod
    def _parse_final_claim(text: str | None) -> tuple[bool, str | None, str | None]:
        if not isinstance(text, str):
            return False, None, "malformed_final_claim"
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return False, None, "malformed_final_claim"
        if not isinstance(parsed, dict) or set(parsed) != {"completion_claimed", "summary"}:
            return False, None, "invalid_final_claim"
        if not isinstance(parsed.get("completion_claimed"), bool) or not isinstance(parsed.get("summary"), str):
            return False, None, "invalid_final_claim"
        return parsed["completion_claimed"], parsed["summary"], None

    @staticmethod
    def _aggregate_usage(responses: list[ResponseRecord]) -> dict[str, Any]:
        rows = [dict(record.usage) for record in responses]
        keys = sorted(
            {
                key
                for row in rows
                for key, value in row.items()
                if isinstance(value, int) and not isinstance(value, bool)
            }
        )
        totals = {
            key: sum(
                row.get(key, 0)
                for row in rows
                if isinstance(row.get(key, 0), int) and not isinstance(row.get(key, 0), bool)
            )
            for key in keys
        }
        return {"responses": rows, "totals": totals}

    @staticmethod
    def _error(code: str, message: str, request_index: int) -> dict[str, Any]:
        return {
            "code": code,
            "message": redact_error_text(message),
            "request_index": request_index,
        }
