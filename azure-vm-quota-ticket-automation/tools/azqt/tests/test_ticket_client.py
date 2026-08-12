"""Mocked HTTP tests for Azure Support ticket creation and polling.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.8, 6.9, 6.10, 7.7, 7.8**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from azqt.azure.payload_mapper import ConfirmedQuotaRequest, group_confirmed_requests
from azqt.azure.problem_classification_cache import MANAGEMENT_ENDPOINT, SUPPORT_API_VERSION
from azqt.azure.ticket_client import TicketClient, support_ticket_name_for_group


@dataclass
class FakeResponse:
    """A controlled HTTP response returned by :class:`MockHttpSession`."""

    status_code: int
    payload: Any
    headers: Mapping[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        return self.payload


class MockHttpSession:
    """Mocked HTTP layer with independently queued create and poll responses."""

    def __init__(
        self, *, put_responses: list[FakeResponse], get_responses: list[FakeResponse] | None = None
    ) -> None:
        self.put_responses = list(put_responses)
        self.get_responses = list(get_responses or [])
        self.put_calls: list[dict[str, Any]] = []
        self.get_calls: list[dict[str, Any]] = []

    def put(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        json: Mapping[str, Any],
        timeout: float,
    ) -> FakeResponse:
        self.put_calls.append(
            {
                "url": url,
                "params": dict(params),
                "headers": dict(headers),
                "json": dict(json),
                "timeout": timeout,
            }
        )
        return self.put_responses.pop(0)

    def get(self, url: str, *, headers: Mapping[str, str], timeout: float) -> FakeResponse:
        self.get_calls.append({"url": url, "headers": dict(headers), "timeout": timeout})
        return self.get_responses.pop(0)


class FakeClock:
    """Monotonic clock advanced only by the client's injected sleep callback."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def group():
    """Return one valid group using the established Payload_Mapper data model."""

    return group_confirmed_requests(
        [
            ConfirmedQuotaRequest(
                candidate_id="candidate-1",
                subscription_id="subscription-a",
                region="EastUS",
                quota_family="standardDSv5Family",
                requested_quota=8,
                justification="Scale a production workload.",
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


PAYLOAD = {"properties": {"title": "Compute VM Cores quota increase"}}
TOKEN = "test-access-token"
OPERATION_URL = "https://management.azure.com/providers/Microsoft.Support/operations/op-1"


def test_200_response_returns_ticket_number_and_status() -> None:
    """HTTP 200 creates a ticket immediately without an operation poll (Req 6.1-6.2)."""

    http = MockHttpSession(
        put_responses=[FakeResponse(200, {"name": "240100000001", "properties": {"status": "Open"}})]
    )
    result = TicketClient(session=http).submit(group(), PAYLOAD, TOKEN)

    expected_name = support_ticket_name_for_group(group())
    assert result.succeeded
    assert result.ticket_number == "240100000001"
    assert result.ticket_status == "Open"
    assert result.support_ticket_name == expected_name
    assert http.get_calls == []
    assert http.put_calls == [
        {
            "url": (
                f"{MANAGEMENT_ENDPOINT}/subscriptions/subscription-a/"
                "providers/Microsoft.Support/supportTickets/"
                f"{expected_name}"
            ),
            "params": {"api-version": SUPPORT_API_VERSION},
            "headers": {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
            "json": PAYLOAD,
            "timeout": 30.0,
        }
    ]


def test_202_response_polls_to_terminal_success_using_retry_after() -> None:
    """HTTP 202 sleeps Retry-After then polls to a usable terminal ticket (Req 6.3-6.4, 6.8)."""

    clock = FakeClock()
    http = MockHttpSession(
        put_responses=[FakeResponse(202, {}, {"Location": OPERATION_URL, "Retry-After": "3"})],
        get_responses=[
            FakeResponse(200, {"status": "InProgress"}, {"Retry-After": "7"}),
            FakeResponse(
                200,
                {
                    "status": "Succeeded",
                    "name": "240100000002",
                    "properties": {"status": "Open"},
                },
            ),
        ],
    )
    result = TicketClient(session=http, clock=clock, sleep=clock.sleep).submit(group(), PAYLOAD, TOKEN)

    assert result.succeeded
    assert result.ticket_number == "240100000002"
    assert result.ticket_status == "Open"
    assert clock.sleeps == [3.0, 7.0]
    assert [call["url"] for call in http.get_calls] == [OPERATION_URL, OPERATION_URL]


def test_202_poll_returning_the_final_ticket_resource_directly_succeeds() -> None:
    """A poll response with no status/provisioningState wrapper still succeeds if it
    is itself a usable ticket resource, since Azure sometimes returns
    SupportTicketDetails directly at the operation URL once the LRO completes."""

    clock = FakeClock()
    http = MockHttpSession(
        put_responses=[FakeResponse(202, {}, {"Location": OPERATION_URL})],
        get_responses=[
            FakeResponse(200, {"name": "240100000009", "properties": {"status": "Open"}}),
        ],
    )
    result = TicketClient(session=http, clock=clock, sleep=clock.sleep).submit(group(), PAYLOAD, TOKEN)

    assert result.succeeded
    assert result.ticket_number == "240100000009"
    assert result.ticket_status == "Open"


def test_202_poll_terminal_failure_is_recorded_as_failed() -> None:
    """An Azure terminal failure never produces a created-ticket result (Req 6.9)."""

    clock = FakeClock()
    http = MockHttpSession(
        put_responses=[FakeResponse(202, {}, {"azure-asyncoperation": OPERATION_URL})],
        get_responses=[FakeResponse(200, {"status": "Failed", "error": {"message": "rejected"}})],
    )
    result = TicketClient(session=http, clock=clock, sleep=clock.sleep).submit(group(), PAYLOAD, TOKEN)

    assert result.outcome == "failed"
    assert result.ticket_number is None
    assert result.ticket_status is None
    assert result.error is not None
    assert "terminal failure state 'Failed'" in result.error
    assert clock.sleeps == [10.0]


def test_202_poll_stops_at_five_minute_cap_without_waiting_past_deadline() -> None:
    """A non-terminal operation ends as timeout at five minutes (Req 6.4-6.5)."""

    clock = FakeClock()
    http = MockHttpSession(
        put_responses=[FakeResponse(202, {}, {"Location": OPERATION_URL, "Retry-After": "1000"})],
        get_responses=[FakeResponse(200, {"status": "Running"})],
    )
    result = TicketClient(session=http, clock=clock, sleep=clock.sleep).submit(group(), PAYLOAD, TOKEN)

    assert result.outcome == "timed_out"
    assert result.error == "Ticket operation timed out after 5 minutes."
    assert clock.sleeps == [300.0]
    assert len(http.get_calls) == 1


def test_malformed_200_response_fails_with_explicit_missing_data_error() -> None:
    """A direct result must include both the support-ticket number and status (Req 6.10)."""

    http = MockHttpSession(put_responses=[FakeResponse(200, {"name": "240100000003"})])
    result = TicketClient(session=http).submit(group(), PAYLOAD, TOKEN)

    assert result.outcome == "failed"
    assert result.error == (
        "Missing response data: HTTP 200 response did not include support ticket number and status."
    )


def test_malformed_202_response_fails_with_explicit_missing_data_error() -> None:
    """An asynchronous result must identify an operation URL before polling (Req 6.10)."""

    http = MockHttpSession(put_responses=[FakeResponse(202, {})])
    result = TicketClient(session=http).submit(group(), PAYLOAD, TOKEN)

    assert result.outcome == "failed"
    assert result.error == (
        "Missing response data: HTTP 202 response did not include an operation status location."
    )
    assert http.get_calls == []


def test_poll_response_with_neither_operation_state_nor_ticket_data_fails() -> None:
    """A poll payload lacking both an operation-state field and usable ticket fields still fails clearly."""

    clock = FakeClock()
    http = MockHttpSession(
        put_responses=[FakeResponse(202, {}, {"Location": OPERATION_URL})],
        get_responses=[FakeResponse(200, {"unrelated": "field"})],
    )
    result = TicketClient(session=http, clock=clock, sleep=clock.sleep).submit(group(), PAYLOAD, TOKEN)

    assert result.outcome == "failed"
    assert result.error == (
        "Missing response data: operation status poll did not include an operation status."
    )


def test_same_group_key_reuses_deterministic_name_and_accepts_existing_ticket() -> None:
    """A repeat creates no new name and treats Azure's existing 200 ticket as the result (Req 7.7-7.8)."""

    http = MockHttpSession(
        put_responses=[
            FakeResponse(200, {"name": "240100000004", "properties": {"status": "Open"}}),
            FakeResponse(200, {"name": "240100000004", "properties": {"status": "Open"}}),
        ]
    )
    client = TicketClient(session=http)

    first = client.submit(group(), PAYLOAD, TOKEN)
    existing = client.submit(group(), PAYLOAD, TOKEN)

    assert first.succeeded and existing.succeeded
    assert existing.ticket_number == first.ticket_number == "240100000004"
    assert existing.support_ticket_name == first.support_ticket_name
    assert http.put_calls[0]["url"] == http.put_calls[1]["url"]
    assert http.put_calls[0]["url"].endswith(f"/{support_ticket_name_for_group(group())}")
