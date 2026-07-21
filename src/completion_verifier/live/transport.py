from __future__ import annotations

from typing import Protocol, Sequence

from .models import (
    LiveRunError,
    ResponseRecord,
    ResponseRequest,
    redact_error_text,
)


class ResponsesTransport(Protocol):
    name: str
    version: str

    def create(self, request: ResponseRequest) -> ResponseRecord:
        ...


class FakeResponsesTransport:
    name = "fake-responses"
    version = "1"

    def __init__(self, fixtures: Sequence[ResponseRecord | BaseException]):
        self._fixtures = list(fixtures)
        self.requests: list[ResponseRequest] = []
        self._index = 0

    def create(self, request: ResponseRequest) -> ResponseRecord:
        self.requests.append(request)
        if self._index >= len(self._fixtures):
            raise LiveRunError("Fake response fixtures are exhausted.")
        fixture = self._fixtures[self._index]
        request_index = self._index
        self._index += 1
        if isinstance(fixture, BaseException):
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
                    "type": type(fixture).__name__,
                    "message": redact_error_text(fixture),
                },
                raw={
                    "status": "transport_error",
                    "error_type": type(fixture).__name__,
                },
            )
        if fixture.request_index == request_index:
            return fixture
        return ResponseRecord(
            response_id=fixture.response_id,
            model=fixture.model,
            status=fixture.status,
            incomplete_details=fixture.incomplete_details,
            output_items=fixture.output_items,
            output_text=fixture.output_text,
            usage=fixture.usage,
            request_index=request_index,
            transport_error=fixture.transport_error,
            raw=fixture.raw,
        )
