"""Retry transient Azure Support API calls with bounded, audited delays.

``RetryHandler`` is deliberately independent of ticket payloads and long-running
operation parsing.  A caller supplies one *individual* HTTP operation (either
the ticket-creation PUT or one operation-status GET) and the handler applies
the same policy to it.  Keeping that boundary at a single HTTP request means
create and poll retries have separate three-retry budgets, as required.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Callable, Generic, Mapping, Protocol, TypeVar

import requests

from azqt.audit.logger import AuditLogger
from azqt.azure.payload_mapper import SubscriptionTicketGroup


class HttpResponse(Protocol):
    """The response attributes needed to classify an Azure API result."""

    status_code: int
    headers: Mapping[str, str]


ResponseT = TypeVar("ResponseT", bound=HttpResponse)


@dataclass(frozen=True)
class PermanentRetryFailure:
    """The final reason a single HTTP request could not be completed."""

    status_code: int | None
    message: str

    @property
    def no_response_received(self) -> bool:
        """Whether the request exhausted retries without any HTTP response."""

        return self.status_code is None

    def __str__(self) -> str:
        if self.status_code is None:
            return f"No response received: {self.message}"
        return f"HTTP {self.status_code}: {self.message}"


@dataclass(frozen=True)
class RetryResult(Generic[ResponseT]):
    """The response or permanent failure for one individual HTTP request."""

    response: ResponseT | None
    failure: PermanentRetryFailure | None
    retry_count: int

    @property
    def succeeded(self) -> bool:
        """Return whether the wrapped request produced a non-retryable response."""

        return self.response is not None and self.failure is None


class RetryHandler:
    """Apply Azure Support retry rules to one create or poll HTTP operation.

    The first call is not a retry.  ``max_retries=3`` therefore permits at
    most four executions of the supplied operation: the initial request plus
    three retries.  All transient causes share that one budget.
    """

    MAX_RETRIES = 3
    DEFAULT_THROTTLE_DELAY_SECONDS = 5.0
    EXPONENTIAL_BACKOFF_SECONDS = (5.0, 10.0, 20.0)
    REQUEST_TIMEOUT_SECONDS = 30.0

    def __init__(
        self,
        *,
        audit_logger: AuditLogger | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_retries: int = MAX_RETRIES,
        request_timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        """Configure the generic handler and its testable timing seams.

        ``request_timeout_seconds`` documents the timeout callers must pass to
        their HTTP library.  The handler classifies a request exception as a
        no-response failure; it does not start an additional worker thread for
        an already synchronous HTTP client.
        """

        if max_retries < 0:
            raise ValueError("max_retries must be non-negative.")
        if request_timeout_seconds <= 0:
            raise ValueError("request_timeout_seconds must be positive.")
        self._audit_logger = audit_logger
        self._sleep = sleep
        self.max_retries = max_retries
        self.request_timeout_seconds = request_timeout_seconds

    def execute(
        self,
        operation: Callable[[], ResponseT],
        group: SubscriptionTicketGroup,
        *,
        action: str,
    ) -> RetryResult[ResponseT]:
        """Run one create or poll operation according to the retry policy.

        A successful HTTP response (including HTTP 202 for the create call) is
        returned unchanged for TicketClient to interpret.  A non-429 4xx is
        permanent immediately; all 5xx responses and requests that raise a
        network exception are retried up to the shared cap.
        """

        retry_count = 0
        while True:
            try:
                response = operation()
            except (requests.RequestException, TimeoutError, ConnectionError, OSError) as exc:
                trigger = _NoResponseTrigger(_exception_message(exc))
                if retry_count >= self.max_retries:
                    return RetryResult(
                        response=None,
                        failure=PermanentRetryFailure(None, trigger.message),
                        retry_count=retry_count,
                    )
                retry_count += 1
                delay = self._backoff_delay(retry_count)
                self._log_retry(group, action, retry_count, delay, trigger)
                self._sleep(delay)
                continue

            status_code = response.status_code
            if 200 <= status_code < 300:
                return RetryResult(response=response, failure=None, retry_count=retry_count)

            if status_code == 429:
                trigger = _ResponseTrigger(status_code, _response_message(response))
                if retry_count >= self.max_retries:
                    return RetryResult(
                        response=None,
                        failure=PermanentRetryFailure(status_code, trigger.message),
                        retry_count=retry_count,
                    )
                retry_count += 1
                delay = _retry_after_seconds(response.headers)
                if delay is None:
                    delay = self.DEFAULT_THROTTLE_DELAY_SECONDS
                self._log_retry(group, action, retry_count, delay, trigger)
                self._sleep(delay)
                continue

            if 500 <= status_code < 600:
                trigger = _ResponseTrigger(status_code, _response_message(response))
                if retry_count >= self.max_retries:
                    return RetryResult(
                        response=None,
                        failure=PermanentRetryFailure(status_code, trigger.message),
                        retry_count=retry_count,
                    )
                retry_count += 1
                delay = self._backoff_delay(retry_count)
                self._log_retry(group, action, retry_count, delay, trigger)
                self._sleep(delay)
                continue

            # Req 7.6 mandates immediate failure for a non-429 4xx.  Other
            # unexpected non-success statuses are also permanent rather than
            # being silently treated as a response TicketClient should parse.
            return RetryResult(
                response=None,
                failure=PermanentRetryFailure(status_code, _response_message(response)),
                retry_count=retry_count,
            )

    def _backoff_delay(self, retry_attempt: int) -> float:
        """Return 5/10/20 seconds for retry attempts one through three."""

        return self.EXPONENTIAL_BACKOFF_SECONDS[retry_attempt - 1]

    def _log_retry(
        self,
        group: SubscriptionTicketGroup,
        action: str,
        retry_attempt: int,
        delay_seconds: float,
        trigger: "_RetryTrigger",
    ) -> None:
        """Best-effort log a retry before its wait without interrupting the run."""

        if self._audit_logger is None:
            return
        data: dict[str, Any] = {
            "subscription_id": group.subscription_id,
            "line_items": [
                {"region": line_item.region, "quota_family": line_item.quota_family}
                for line_item in group.line_items
            ],
            "action": action,
            "retry_attempt": retry_attempt,
            "delay_seconds": delay_seconds,
        }
        if trigger.status_code is None:
            data["error"] = trigger.message
        else:
            data["http_status_code"] = trigger.status_code
            data["error"] = trigger.message
        self._audit_logger.log("api-retry", data)


@dataclass(frozen=True)
class _RetryTrigger:
    status_code: int | None
    message: str


class _NoResponseTrigger(_RetryTrigger):
    def __init__(self, message: str) -> None:
        super().__init__(None, message)


class _ResponseTrigger(_RetryTrigger):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(status_code, message)


def _retry_after_seconds(headers: Mapping[str, str]) -> float | None:
    """Return a finite non-negative Retry-After duration in seconds, if valid."""

    raw_value = _header(headers, "Retry-After")
    if raw_value is None:
        return None
    try:
        value = float(raw_value.strip())
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value >= 0 else None


def _header(headers: Mapping[str, str], name: str) -> str | None:
    """Look up a header case-insensitively for requests and test doubles."""

    for key, value in headers.items():
        if key.casefold() == name.casefold() and isinstance(value, str):
            return value
    return None


def _response_message(response: HttpResponse) -> str:
    """Extract the server's concise error text without depending on requests.Response.

    Azure's top-level ``error.message`` is often a generic phrase (e.g. "The
    calling client sent a bad request to the service"); the actionable cause
    is usually in ``error.details[].message`` instead, so both are appended
    when present rather than silently dropping the detail.
    """

    json_method = getattr(response, "json", None)
    if callable(json_method):
        try:
            payload = json_method()
        except (TypeError, ValueError):
            payload = None
        if isinstance(payload, Mapping):
            error = payload.get("error")
            if isinstance(error, Mapping):
                message = error.get("message")
                if isinstance(message, str) and message.strip():
                    detail_messages = [
                        detail["message"].strip()
                        for detail in error.get("details", [])
                        if isinstance(detail, Mapping)
                        and isinstance(detail.get("message"), str)
                        and detail["message"].strip()
                    ]
                    if detail_messages:
                        return message.strip() + " (" + "; ".join(detail_messages) + ")"
                    return message.strip()
            message = payload.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()

    reason = getattr(response, "reason", None)
    if isinstance(reason, str) and reason.strip():
        return reason.strip()
    return "Azure Support API request failed."


def _exception_message(exc: BaseException) -> str:
    """Render a useful no-response cause while retaining the required wording."""

    message = str(exc).strip()
    return message or type(exc).__name__


# The design calls this component Retry_Handler.  The conventional Python name
# is exported together with this alias so callers can use either terminology.
Retry_Handler = RetryHandler
