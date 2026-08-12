"""Unit tests for bounded, audited Azure Support API retries.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 9.10**
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import requests

from azqt.audit.logger import AuditLogger
from azqt.azure.payload_mapper import ConfirmedQuotaRequest, group_confirmed_requests
from azqt.azure.retry import RetryHandler


@dataclass
class FakeResponse:
    """Small HTTP response double exposing only retry-classification fields."""

    status_code: int
    payload: Any = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)
    reason: str | None = None

    def json(self) -> Any:
        return self.payload


class SequencedOperation:
    """Return or raise controlled outcomes while counting individual requests."""

    def __init__(self, outcomes: list[FakeResponse | BaseException]) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self) -> FakeResponse:
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def group():
    """Return the existing payload-mapper group shape used in retry log entries."""

    return group_confirmed_requests(
        [
            ConfirmedQuotaRequest(
                candidate_id="candidate-1",
                subscription_id="subscription-a",
                region="EastUS",
                quota_family="standardDSv5Family",
                requested_quota=8,
                justification="Scale workload.",
                contact_name="Ada Lovelace",
                contact_email="ada@example.test",
                contact_phone=None,
                country="USA",
                preferred_time_zone="Pacific Standard Time",
                preferred_support_language="en-us",
                severity_level="moderate",
            )
        ]
    )[0]


def retry_events(log_path: Path) -> list[dict[str, Any]]:
    """Read only the Retry_Handler events from the append-only log."""

    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if json.loads(line)["event_type"] == "api-retry"
    ]


def test_429_with_valid_retry_after_waits_that_duration_and_logs_attempt(tmp_path: Path) -> None:
    """A valid 429 Retry-After duration controls the sole retry wait (Req 7.1, 9.10)."""

    log_path = tmp_path / "run.jsonl"
    waits: list[float] = []
    operation = SequencedOperation(
        [
            FakeResponse(429, {"error": {"message": "slow down"}}, {"retry-after": "2.5"}),
            FakeResponse(200),
        ]
    )

    result = RetryHandler(audit_logger=AuditLogger(log_path), sleep=waits.append).execute(
        operation, group(), action="ticket-creation"
    )

    assert result.succeeded
    assert result.retry_count == 1
    assert operation.calls == 2
    assert waits == [2.5]
    event = retry_events(log_path)[0]["data"]
    assert event == {
        "subscription_id": "subscription-a",
        "line_items": [{"region": "EastUS", "quota_family": "standardDSv5Family"}],
        "action": "ticket-creation",
        "retry_attempt": 1,
        "delay_seconds": 2.5,
        "http_status_code": 429,
        "error": "slow down",
    }


def test_429_without_or_with_invalid_retry_after_uses_five_second_default() -> None:
    """Absent and invalid throttle durations both use the documented five seconds (Req 7.2)."""

    for headers in ({}, {"Retry-After": "not-a-duration"}, {"Retry-After": "-1"}):
        waits: list[float] = []
        operation = SequencedOperation([FakeResponse(429, headers=headers), FakeResponse(200)])

        result = RetryHandler(sleep=waits.append).execute(operation, group(), action="poll")

        assert result.succeeded
        assert waits == [5.0]


def test_5xx_uses_5_10_20_exponential_backoff_and_allows_three_retries() -> None:
    """Three server failures consume the full retry budget before a fourth success (Req 7.3-7.4)."""

    waits: list[float] = []
    operation = SequencedOperation(
        [
            FakeResponse(500, {"error": {"message": "server one"}}),
            FakeResponse(502, {"error": {"message": "server two"}}),
            FakeResponse(503, {"error": {"message": "server three"}}),
            FakeResponse(200),
        ]
    )

    result = RetryHandler(sleep=waits.append).execute(operation, group(), action="poll")

    assert result.succeeded
    assert result.retry_count == 3
    assert operation.calls == 4
    assert waits == [5.0, 10.0, 20.0]


def test_connection_timeouts_use_the_same_exponential_backoff() -> None:
    """No-response network failures retry with the 5/10/20 sequence (Req 7.3)."""

    waits: list[float] = []
    operation = SequencedOperation(
        [
            requests.Timeout("first timeout"),
            requests.ConnectionError("connection unavailable"),
            requests.Timeout("third timeout"),
            FakeResponse(202),
        ]
    )

    result = RetryHandler(sleep=waits.append).execute(operation, group(), action="ticket-creation")

    assert result.succeeded
    assert result.response is not None and result.response.status_code == 202
    assert result.retry_count == 3
    assert waits == [5.0, 10.0, 20.0]


def test_non_429_4xx_is_permanent_without_retry() -> None:
    """A client error other than throttling is returned immediately (Req 7.6)."""

    waits: list[float] = []
    operation = SequencedOperation(
        [FakeResponse(400, {"error": {"message": "invalid contact"}}), FakeResponse(200)]
    )

    result = RetryHandler(sleep=waits.append).execute(operation, group(), action="ticket-creation")

    assert not result.succeeded
    assert result.retry_count == 0
    assert result.failure is not None
    assert result.failure.status_code == 400
    assert str(result.failure) == "HTTP 400: invalid contact"
    assert operation.calls == 1
    assert waits == []


def test_retries_exhausted_returns_last_status_and_writes_one_event_per_retry(tmp_path: Path) -> None:
    """The fourth transient response permanently fails and only prior retries are logged (Req 7.4-7.5, 9.10)."""

    log_path = tmp_path / "run.jsonl"
    waits: list[float] = []
    operation = SequencedOperation(
        [
            FakeResponse(503, {"error": {"message": "temporary one"}}),
            FakeResponse(429, {"error": {"message": "temporary two"}}, {"Retry-After": "1"}),
            FakeResponse(500, {"error": {"message": "temporary three"}}),
            FakeResponse(503, {"error": {"message": "final failure"}}),
        ]
    )

    result = RetryHandler(audit_logger=AuditLogger(log_path), sleep=waits.append).execute(
        operation, group(), action="poll"
    )

    assert not result.succeeded
    assert result.response is None
    assert result.retry_count == 3
    assert result.failure is not None
    assert result.failure.status_code == 503
    assert str(result.failure) == "HTTP 503: final failure"
    assert operation.calls == 4
    assert waits == [5.0, 1.0, 20.0]

    events = retry_events(log_path)
    assert len(events) == 3
    assert [event["data"]["retry_attempt"] for event in events] == [1, 2, 3]
    assert [event["data"]["http_status_code"] for event in events] == [503, 429, 500]


def test_retries_exhausted_after_timeouts_reports_no_response_received() -> None:
    """A request with no final HTTP response reports the explicit required indication (Req 7.5)."""

    operation = SequencedOperation([requests.Timeout("request timed out")] * 4)

    result = RetryHandler(sleep=lambda _: None).execute(operation, group(), action="poll")

    assert not result.succeeded
    assert result.failure is not None
    assert result.failure.no_response_received
    assert str(result.failure) == "No response received: request timed out"
    assert result.retry_count == 3
