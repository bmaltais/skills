"""Create and poll Azure Support tickets.

This module owns the deterministic request name and long-running-operation
semantics for a single quota-request group.  It can wrap each individual HTTP
create or poll request in the task-12 retry policy while retaining independent
retry budgets for those requests.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping, Protocol

import requests

from azqt.azure.payload_mapper import SubscriptionTicketGroup
from azqt.azure.problem_classification_cache import MANAGEMENT_ENDPOINT, SUPPORT_API_VERSION
from azqt.azure.retry import RetryHandler


class _HttpResponse(Protocol):
    """The subset of a ``requests.Response`` used by :class:`TicketClient`."""

    status_code: int
    headers: Mapping[str, str]

    def json(self) -> Any:
        """Decode the response payload."""


class _HttpSession(Protocol):
    """The authenticated HTTP operations required for ticket submission."""

    def put(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        json: Mapping[str, Any],
        timeout: float,
    ) -> _HttpResponse:
        """Create or retrieve an idempotently named support ticket."""

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout: float,
    ) -> _HttpResponse:
        """Poll an Azure long-running operation endpoint."""


TicketOutcome = Literal["created", "failed", "timed_out"]
ActionOutcomeCallback = Callable[[str, str, str | None], None]


@dataclass(frozen=True)
class TicketSubmissionResult:
    """The complete outcome of one Azure Support ticket create request."""

    outcome: TicketOutcome
    support_ticket_name: str
    ticket_number: str | None = None
    ticket_status: str | None = None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        """Whether Azure produced a usable support ticket."""

        return self.outcome == "created"


_OPERATION_SUCCESS_STATES = frozenset({"succeeded", "success", "completed"})
_OPERATION_FAILURE_STATES = frozenset({"failed", "canceled", "cancelled", "error"})
_OPERATION_PENDING_STATES = frozenset(
    {"accepted", "inprogress", "notstarted", "pending", "running"}
)
_SUCCESSFUL_TICKET_STATUSES = frozenset(
    {"active", "closed", "created", "inprogress", "open", "pending", "resolved"}
)


def _normalise_state(value: str) -> str:
    """Canonicalize Azure status spelling without guessing its meaning."""

    return "".join(character for character in value.casefold() if character.isalnum())


def support_ticket_name_for_group(group: SubscriptionTicketGroup) -> str:
    """Return Azure-safe deterministic ticket name derived from the group key.

    The name is derived from the subscription and the full, sorted set of
    region/quota-family line items, so resubmitting the same request set is
    idempotent while a different combination of line items yields a
    different ticket name.
    """

    line_item_keys = sorted(
        f"{line_item.region.casefold()}\x1e{line_item.quota_family}"
        for line_item in group.line_items
    )
    group_key = "\x1f".join((group.subscription_id, *line_item_keys))
    digest = hashlib.sha256(group_key.encode("utf-8")).hexdigest()[:32]
    return f"azqt-{digest}"


def _header(headers: Mapping[str, str], name: str) -> str | None:
    """Read an HTTP header from either requests or a simple mocked mapping."""

    for key, value in headers.items():
        if key.casefold() == name.casefold() and isinstance(value, str):
            return value
    return None


def _retry_after_seconds(headers: Mapping[str, str]) -> float | None:
    """Read a valid non-negative Retry-After delay expressed in seconds."""

    raw_value = _header(headers, "Retry-After")
    if raw_value is None:
        return None
    try:
        parsed = float(raw_value.strip())
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _json_object(response: _HttpResponse) -> Mapping[str, Any] | None:
    """Decode an object response body without leaking decoder implementation details."""

    try:
        payload = response.json()
    except (ValueError, TypeError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _nonempty_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _extract_ticket(payload: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """Extract a ticket number/status from documented and common Azure shapes."""

    properties = payload.get("properties")
    property_values = properties if isinstance(properties, Mapping) else {}
    ticket_number = next(
        (
            value
            for value in (
                _nonempty_text(payload.get("ticketNumber")),
                _nonempty_text(payload.get("ticket_number")),
                _nonempty_text(payload.get("name")),
                _nonempty_text(property_values.get("ticketNumber")),
                _nonempty_text(property_values.get("ticket_number")),
            )
            if value is not None
        ),
        None,
    )
    ticket_status = next(
        (
            value
            for value in (
                _nonempty_text(property_values.get("status")),
                _nonempty_text(payload.get("ticketStatus")),
                _nonempty_text(payload.get("status")),
            )
            if value is not None
        ),
        None,
    )
    return ticket_number, ticket_status


def _operation_state(payload: Mapping[str, Any]) -> str | None:
    """Read the long-running operation state, not the support-ticket status."""

    direct = _nonempty_text(payload.get("status"))
    if direct is not None:
        return direct
    properties = payload.get("properties")
    if isinstance(properties, Mapping):
        return _nonempty_text(properties.get("provisioningState"))
    return None


class TicketClient:
    """Call the Azure Support create API and resolve HTTP 202 operations."""

    def __init__(
        self,
        *,
        session: _HttpSession | None = None,
        request_timeout_seconds: float = 30.0,
        poll_deadline_seconds: float = 300.0,
        default_poll_wait_seconds: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        retry_handler: RetryHandler | None = None,
        action_outcome_callback: ActionOutcomeCallback | None = None,
    ) -> None:
        """Create a client with injectable I/O, retry, timing, and audit seams."""

        if request_timeout_seconds <= 0:
            raise ValueError("request_timeout_seconds must be positive.")
        if poll_deadline_seconds <= 0:
            raise ValueError("poll_deadline_seconds must be positive.")
        if default_poll_wait_seconds < 0:
            raise ValueError("default_poll_wait_seconds must be non-negative.")
        self._session = session or requests.Session()
        self._request_timeout_seconds = request_timeout_seconds
        self._poll_deadline_seconds = poll_deadline_seconds
        self._default_poll_wait_seconds = default_poll_wait_seconds
        self._clock = clock
        self._sleep = sleep
        self._retry_handler = retry_handler
        self._action_outcome_callback = action_outcome_callback

    def submit(
        self,
        group: SubscriptionTicketGroup,
        payload: Mapping[str, Any],
        access_token: str,
    ) -> TicketSubmissionResult:
        """Create ``group``'s support ticket, polling an asynchronous response."""

        if not access_token:
            raise ValueError("access_token must be non-empty.")
        support_ticket_name = support_ticket_name_for_group(group)
        url = (
            f"{MANAGEMENT_ENDPOINT}/subscriptions/{group.subscription_id}"
            "/providers/Microsoft.Support/supportTickets/"
            f"{support_ticket_name}"
        )
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        started_at = self._clock()
        response, retry_failure = self._execute_request(
            lambda: self._session.put(
                url,
                params={"api-version": SUPPORT_API_VERSION},
                headers=headers,
                json=payload,
                timeout=self._request_timeout_seconds,
            ),
            group,
            action="ticket-creation",
        )
        if retry_failure is not None:
            result = self._failed(support_ticket_name, retry_failure)
            self._record_result("ticket-creation", result)
            return result
        assert response is not None

        if response.status_code == 200:
            result = self._ticket_from_direct_response(support_ticket_name, response)
            self._record_result("ticket-creation", result)
            return result
        if response.status_code != 202:
            result = self._failed(
                support_ticket_name,
                f"HTTP {response.status_code}: ticket creation request failed.",
            )
            self._record_result("ticket-creation", result)
            return result

        operation_location = _header(response.headers, "Location") or _header(
            response.headers, "azure-asyncoperation"
        )
        if operation_location is None or not operation_location.strip():
            result = self._failed(
                support_ticket_name,
                "Missing response data: HTTP 202 response did not include an operation status location.",
            )
            self._record_result("ticket-creation", result)
            return result
        self._record_action("ticket-creation", "success", None)
        return self._poll_operation(
            group=group,
            support_ticket_name=support_ticket_name,
            operation_location=operation_location,
            headers=headers,
            initial_retry_after_seconds=_retry_after_seconds(response.headers),
            started_at=started_at,
        )

    def _execute_request(
        self,
        operation: Callable[[], _HttpResponse],
        group: SubscriptionTicketGroup,
        *,
        action: str,
    ) -> tuple[_HttpResponse | None, str | None]:
        """Run one HTTP request with the configured bounded retry policy."""

        if self._retry_handler is None:
            try:
                return operation(), None
            except requests.RequestException as exc:
                return None, str(exc)
        result = self._retry_handler.execute(operation, group, action=action)
        if result.failure is not None:
            return None, str(result.failure)
        return result.response, None

    def _ticket_from_direct_response(
        self, support_ticket_name: str, response: _HttpResponse
    ) -> TicketSubmissionResult:
        payload = _json_object(response)
        if payload is None:
            return self._failed(
                support_ticket_name,
                "Missing response data: HTTP 200 response did not contain a ticket object.",
            )
        ticket_number, ticket_status = _extract_ticket(payload)
        if ticket_number is None or ticket_status is None:
            return self._failed(
                support_ticket_name,
                "Missing response data: HTTP 200 response did not include support ticket number and status.",
            )
        return TicketSubmissionResult(
            outcome="created",
            support_ticket_name=support_ticket_name,
            ticket_number=ticket_number,
            ticket_status=ticket_status,
        )

    def _poll_operation(
        self,
        *,
        group: SubscriptionTicketGroup,
        support_ticket_name: str,
        operation_location: str,
        headers: Mapping[str, str],
        initial_retry_after_seconds: float | None,
        started_at: float,
    ) -> TicketSubmissionResult:
        """Wait and poll until Azure reaches a known terminal state or deadline."""

        retry_after_seconds = initial_retry_after_seconds
        deadline = started_at + self._poll_deadline_seconds
        while True:
            remaining_seconds = deadline - self._clock()
            if remaining_seconds < 0:
                result = self._timed_out(support_ticket_name)
                self._record_result("ticket-operation-poll", result)
                return result

            requested_wait = (
                retry_after_seconds
                if retry_after_seconds is not None
                else self._default_poll_wait_seconds
            )
            wait_seconds = min(requested_wait, remaining_seconds)
            if wait_seconds > 0:
                self._sleep(wait_seconds)

            response, retry_failure = self._execute_request(
                lambda: self._session.get(
                    operation_location,
                    headers=headers,
                    timeout=self._request_timeout_seconds,
                ),
                group,
                action="ticket-operation-poll",
            )
            if retry_failure is not None:
                result = self._failed(support_ticket_name, retry_failure)
                self._record_result("ticket-operation-poll", result)
                return result
            assert response is not None

            if not 200 <= response.status_code < 300:
                result = self._failed(
                    support_ticket_name,
                    f"HTTP {response.status_code}: ticket operation status poll failed.",
                )
                self._record_result("ticket-operation-poll", result)
                return result
            payload = _json_object(response)
            if payload is None:
                result = self._failed(
                    support_ticket_name,
                    "Missing response data: operation status poll did not contain an object.",
                )
                self._record_result("ticket-operation-poll", result)
                return result

            operation_state = _operation_state(payload)
            if operation_state is None:
                # Azure sometimes finishes the LRO by returning the final
                # SupportTicketDetails resource directly at the operation URL
                # (properties.status, not a status/provisioningState
                # wrapper) -- try that shape before declaring failure.
                terminal_result = self._ticket_from_terminal_response(support_ticket_name, payload)
                if terminal_result.succeeded:
                    self._record_result("ticket-operation-poll", terminal_result)
                    return terminal_result
                result = self._failed(
                    support_ticket_name,
                    "Missing response data: operation status poll did not include an operation status.",
                )
                self._record_result("ticket-operation-poll", result)
                return result
            normalized_state = _normalise_state(operation_state)
            if normalized_state in _OPERATION_FAILURE_STATES:
                result = self._failed(
                    support_ticket_name,
                    f"Ticket operation reached terminal failure state {operation_state!r}.",
                )
                self._record_result("ticket-operation-poll", result)
                return result
            if normalized_state in _OPERATION_SUCCESS_STATES:
                result = self._ticket_from_terminal_response(support_ticket_name, payload)
                self._record_result("ticket-operation-poll", result)
                return result
            if normalized_state not in _OPERATION_PENDING_STATES:
                result = self._failed(
                    support_ticket_name,
                    f"Ticket operation returned unrecognized status {operation_state!r}.",
                )
                self._record_result("ticket-operation-poll", result)
                return result

            retry_after_seconds = _retry_after_seconds(response.headers)
            if self._clock() >= deadline:
                result = self._timed_out(support_ticket_name)
                self._record_result("ticket-operation-poll", result)
                return result

    def _record_result(self, action: str, result: TicketSubmissionResult) -> None:
        outcome = "success" if result.succeeded else "timeout" if result.outcome == "timed_out" else "failure"
        self._record_action(action, outcome, result.error)

    def _record_action(self, action: str, outcome: str, error: str | None) -> None:
        if self._action_outcome_callback is not None:
            self._action_outcome_callback(action, outcome, error)

    def _ticket_from_terminal_response(
        self, support_ticket_name: str, payload: Mapping[str, Any]
    ) -> TicketSubmissionResult:
        """Validate the final LRO response before declaring ticket creation successful."""

        ticket_number, ticket_status = _extract_ticket(payload)
        if ticket_number is None or ticket_status is None:
            return self._failed(
                support_ticket_name,
                "Missing response data: terminal operation response did not include support ticket number and status.",
            )
        if _normalise_state(ticket_status) not in _SUCCESSFUL_TICKET_STATUSES:
            return self._failed(
                support_ticket_name,
                f"Ticket operation completed with unrecognized or failed ticket status {ticket_status!r}.",
            )
        return TicketSubmissionResult(
            outcome="created",
            support_ticket_name=support_ticket_name,
            ticket_number=ticket_number,
            ticket_status=ticket_status,
        )

    @staticmethod
    def _failed(support_ticket_name: str, error: str) -> TicketSubmissionResult:
        return TicketSubmissionResult(
            outcome="failed", support_ticket_name=support_ticket_name, error=error
        )

    @staticmethod
    def _timed_out(support_ticket_name: str) -> TicketSubmissionResult:
        return TicketSubmissionResult(
            outcome="timed_out",
            support_ticket_name=support_ticket_name,
            error="Ticket operation timed out after 5 minutes.",
        )
