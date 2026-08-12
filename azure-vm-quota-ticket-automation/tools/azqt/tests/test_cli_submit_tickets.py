"""Integration-style CLI tests for ``azqt submit-tickets``.

These tests keep AAD and Azure Support HTTP local while exercising the real
CLI orchestration, GUID cache, payload mapper, ticket client, and retry wiring.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
from unittest.mock import ANY

import pytest

import azqt.cli as cli
import azqt.submission.run as submission_run
from azqt.azure.auth import (
    AZURE_CLIENT_CERTIFICATE_ENV,
    AZURE_CLIENT_ID_ENV,
    AZURE_CLIENT_SECRET_ENV,
    AZURE_TENANT_ID_ENV,
    AuthRenewalError,
    AzureAuthProvider,
)
from azqt.azure.problem_classification_cache import (
    COMPUTE_VM_CORES_DISPLAY_NAME,
    QUOTA_SERVICE_DISPLAY_NAME,
    ProblemClassificationCache,
)
from azqt.azure.ticket_client import TicketClient
from azqt.runstate.init_run import init_run


@dataclass
class FakeResponse:
    """Response double covering both Azure Support list and ticket endpoints."""

    status_code: int = 200
    payload: Any = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)
    reason: str | None = None

    def json(self) -> Any:
        return self.payload

    def raise_for_status(self) -> None:
        if not 200 <= self.status_code < 300:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeAadApplication:
    """A deterministic AAD client-credentials substitute."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = iter(responses)
        self.scopes: list[tuple[str, ...]] = []

    def acquire_token_for_client(self, *, scopes: tuple[str, ...]) -> dict[str, Any]:
        self.scopes.append(scopes)
        return next(self._responses)


class ClassificationSession:
    """Mock Services and ProblemClassifications endpoints, recording cache use."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        self.calls.append({"url": url, "headers": dict(headers), "params": dict(params)})
        if url.endswith("/services"):
            return FakeResponse(
                payload={
                    "value": [
                        {
                            "name": "quota-service-guid",
                            "id": "/providers/Microsoft.Support/services/quota-service-guid",
                            "properties": {"displayName": QUOTA_SERVICE_DISPLAY_NAME},
                        }
                    ]
                }
            )
        if url.endswith("/problemClassifications"):
            return FakeResponse(
                payload={
                    "value": [
                        {
                            "name": "compute-cores-guid",
                            "id": (
                                "/providers/Microsoft.Support/services/quota-service-guid"
                                "/problemClassifications/compute-cores-guid"
                            ),
                            "properties": {"displayName": COMPUTE_VM_CORES_DISPLAY_NAME},
                        }
                    ]
                }
            )
        raise AssertionError(f"Unexpected classification URL: {url}")


class TicketSession:
    """Queue mocked create and operation-status responses while recording calls."""

    def __init__(self, *, puts: list[FakeResponse], polls: list[FakeResponse]) -> None:
        self._puts = list(puts)
        self._polls = list(polls)
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
        self.put_calls.append({"url": url, "headers": dict(headers), "json": dict(json)})
        return self._puts.pop(0)

    def get(self, url: str, *, headers: Mapping[str, str], timeout: float) -> FakeResponse:
        self.get_calls.append({"url": url, "headers": dict(headers)})
        return self._polls.pop(0)


class FakeAccessToken:
    """Redacted-token-shaped double used to force a renewal failure in the CLI."""

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal(self) -> str:
        return self._value


class RenewalFailureAuth:
    """Return a cached token once, then fail the next per-group renewal request."""

    def __init__(self) -> None:
        self.calls = 0

    def get_access_token(self) -> FakeAccessToken:
        self.calls += 1
        if self.calls == 3:
            raise AuthRenewalError("Azure AD access-token renewal failed: denied")
        return FakeAccessToken("token-that-must-not-be-logged")


def _request(candidate_id: str, subscription_id: str, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "candidate_id": candidate_id,
        "subscription_id": subscription_id,
        "region": "eastus",
        "quota_family": "standardDSv5Family",
        "requested_quota": 8,
        "justification": f"Scale {candidate_id}.",
        "contact_name": "Ada Lovelace",
        "contact_email": "ada@example.test",
        "contact_phone": None,
        "country": "USA",
        "preferred_time_zone": "Pacific Standard Time",
        "preferred_support_language": "en-us",
        "severity_level": "moderate",
    }
    values.update(overrides)
    return values


def _start_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, Path]:
    monkeypatch.setenv("AZQT_STATE_DIR", str(tmp_path))
    run = init_run("quota-request.txt", state_dir=tmp_path)
    return run["run_id"], run["log_path"]


def _events(log_path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]


def _configure_actual_aad(
    monkeypatch: pytest.MonkeyPatch, application: FakeAadApplication
) -> None:
    monkeypatch.setenv(AZURE_TENANT_ID_ENV, "tenant-id")
    monkeypatch.setenv(AZURE_CLIENT_ID_ENV, "client-id")
    monkeypatch.setenv(AZURE_CLIENT_SECRET_ENV, "client-secret-that-must-not-leak")
    monkeypatch.delenv(AZURE_CLIENT_CERTIFICATE_ENV, raising=False)
    monkeypatch.setattr(
        submission_run,
        "AzureAuthProvider",
        lambda: AzureAuthProvider(application_factory=lambda **_kwargs: application),
    )


def test_submit_tickets_mixed_200_poll_permanent_failure_and_contact_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The complete command isolates each mixed group outcome and audits all work."""

    run_id, log_path = _start_run(tmp_path, monkeypatch)
    input_path = tmp_path / "confirmed_requests.json"
    input_path.write_text(
        json.dumps(
            [
                _request("direct", "subscription-direct"),
                _request("async", "subscription-async"),
                _request("permanent", "subscription-permanent"),
                _request("mismatch-one", "subscription-mismatch"),
                _request(
                    "mismatch-two",
                    "subscription-mismatch",
                    contact_email="different@example.test",
                ),
            ]
        ),
        encoding="utf-8",
    )

    aad = FakeAadApplication([{"access_token": "aad-token-not-for-output", "expires_in": 3600}])
    _configure_actual_aad(monkeypatch, aad)
    classifications = ClassificationSession()
    ticket_http = TicketSession(
        puts=[
            FakeResponse(200, {"name": "TICKET-200", "properties": {"status": "Open"}}),
            FakeResponse(202, {}, {"Location": "https://operations.test/op-1"}),
            FakeResponse(400, {"error": {"message": "invalid quota request"}}),
        ],
        polls=[
            FakeResponse(
                200,
                {"status": "Succeeded", "name": "TICKET-202", "properties": {"status": "Open"}},
            )
        ],
    )
    monkeypatch.setattr(
        submission_run,
        "ProblemClassificationCache",
        lambda: ProblemClassificationCache(session=classifications),
    )
    monkeypatch.setattr(
        submission_run,
        "TicketClient",
        lambda **kwargs: TicketClient(session=ticket_http, sleep=lambda _seconds: None, **kwargs),
    )

    exit_code = cli.main(["submit-tickets", "--run", run_id, "--input", str(input_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "results": [
            {
                "group_key": {
                    "subscription_id": "subscription-direct",
                    "line_items": [{"region": "eastus", "quota_family": "standardDSv5Family"}],
                },
                "status": "created",
                "ticket_number": "TICKET-200",
                "ticket_status": "Open",
                "error": None,
            },
            {
                "group_key": {
                    "subscription_id": "subscription-async",
                    "line_items": [{"region": "eastus", "quota_family": "standardDSv5Family"}],
                },
                "status": "created",
                "ticket_number": "TICKET-202",
                "ticket_status": "Open",
                "error": None,
            },
            {
                "group_key": {
                    "subscription_id": "subscription-permanent",
                    "line_items": [{"region": "eastus", "quota_family": "standardDSv5Family"}],
                },
                "status": "failed",
                "ticket_number": None,
                "ticket_status": None,
                "error": "HTTP 400: invalid quota request",
            },
            {
                "group_key": {
                    "subscription_id": "subscription-mismatch",
                    "line_items": [{"region": "eastus", "quota_family": "standardDSv5Family"}],
                },
                "status": "failed",
                "ticket_number": None,
                "ticket_status": None,
                "error": ANY,
            },
        ]
    }
    assert "contact_email" in payload["results"][-1]["error"]
    assert len(classifications.calls) == 2
    assert len(ticket_http.put_calls) == 3
    assert len(ticket_http.get_calls) == 1

    events = _events(log_path)
    excluded = [event for event in events if event["event_type"] == "quota-request-group-excluded"]
    received = [event for event in events if event["event_type"] == "support-ticket-received"]
    outcomes = [event["data"] for event in events if event["event_type"] == "submission-outcome"]
    assert len(excluded) == 1
    assert "contact_email" in excluded[0]["data"]["reason"]
    assert [event["data"]["ticket_number"] for event in received] == ["TICKET-200", "TICKET-202"]
    assert {("ticket-creation", "success"), ("ticket-operation-poll", "success")} <= {
        (outcome["action"], outcome["outcome"]) for outcome in outcomes
    }
    audit_text = log_path.read_text(encoding="utf-8")
    assert "aad-token-not-for-output" not in audit_text
    assert "client-secret-that-must-not-leak" not in audit_text


def test_submit_tickets_stops_after_a_mid_run_token_renewal_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A renewal failure marks every remaining submit-ready group failed without new PUTs."""

    run_id, log_path = _start_run(tmp_path, monkeypatch)
    input_path = tmp_path / "confirmed_requests.json"
    input_path.write_text(
        json.dumps([_request("first", "subscription-one"), _request("second", "subscription-two")]),
        encoding="utf-8",
    )
    auth = RenewalFailureAuth()
    classifications = ClassificationSession()
    ticket_http = TicketSession(
        puts=[FakeResponse(200, {"name": "TICKET-FIRST", "properties": {"status": "Open"}})],
        polls=[],
    )
    monkeypatch.setattr(submission_run, "AzureAuthProvider", lambda: auth)
    monkeypatch.setattr(
        submission_run,
        "ProblemClassificationCache",
        lambda: ProblemClassificationCache(session=classifications),
    )
    monkeypatch.setattr(
        submission_run,
        "TicketClient",
        lambda **kwargs: TicketClient(session=ticket_http, sleep=lambda _seconds: None, **kwargs),
    )

    exit_code = cli.main(["submit-tickets", "--run", run_id, "--input", str(input_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert [result["status"] for result in payload["results"]] == ["created", "failed"]
    assert payload["results"][1]["error"] == "Azure AD access-token renewal failed: denied"
    assert len(ticket_http.put_calls) == 1
    renewal_events = [
        event["data"]
        for event in _events(log_path)
        if event["event_type"] == "submission-outcome"
        and event["data"]["action"] == "access-token-renewal"
    ]
    assert renewal_events == [
        {
            "subscription_id": "subscription-two",
            "line_items": [{"region": "eastus", "quota_family": "standardDSv5Family"}],
            "action": "access-token-renewal",
            "outcome": "failure",
            "error": "Azure AD access-token renewal failed: denied",
        }
    ]


def test_submit_tickets_combines_same_subscription_requests_into_one_ticket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Requests for one subscription across regions/families produce a single ticket."""

    run_id, log_path = _start_run(tmp_path, monkeypatch)
    input_path = tmp_path / "confirmed_requests.json"
    input_path.write_text(
        json.dumps(
            [
                _request(
                    "combined-one",
                    "subscription-combined",
                    region="eastus",
                    quota_family="standardDASv6Family",
                    requested_quota=4,
                ),
                _request(
                    "combined-two",
                    "subscription-combined",
                    region="westus",
                    quota_family="standardEASv6Family",
                    requested_quota=8,
                ),
                _request("other-subscription", "subscription-other"),
            ]
        ),
        encoding="utf-8",
    )

    aad = FakeAadApplication([{"access_token": "aad-token-not-for-output", "expires_in": 3600}])
    _configure_actual_aad(monkeypatch, aad)
    classifications = ClassificationSession()
    ticket_http = TicketSession(
        puts=[
            FakeResponse(200, {"name": "TICKET-COMBINED", "properties": {"status": "Open"}}),
            FakeResponse(200, {"name": "TICKET-OTHER", "properties": {"status": "Open"}}),
        ],
        polls=[],
    )
    monkeypatch.setattr(
        submission_run,
        "ProblemClassificationCache",
        lambda: ProblemClassificationCache(session=classifications),
    )
    monkeypatch.setattr(
        submission_run,
        "TicketClient",
        lambda **kwargs: TicketClient(session=ticket_http, sleep=lambda _seconds: None, **kwargs),
    )

    exit_code = cli.main(["submit-tickets", "--run", run_id, "--input", str(input_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    # Two subscriptions in the confirmed requests still produce exactly two
    # tickets -- one HTTP PUT each -- with the two-region/family subscription
    # combined into a single ticket instead of two.
    assert len(ticket_http.put_calls) == 2
    assert payload == {
        "results": [
            {
                "group_key": {
                    "subscription_id": "subscription-combined",
                    "line_items": [
                        {"region": "eastus", "quota_family": "standardDASv6Family"},
                        {"region": "westus", "quota_family": "standardEASv6Family"},
                    ],
                },
                "status": "created",
                "ticket_number": "TICKET-COMBINED",
                "ticket_status": "Open",
                "error": None,
            },
            {
                "group_key": {
                    "subscription_id": "subscription-other",
                    "line_items": [{"region": "eastus", "quota_family": "standardDSv5Family"}],
                },
                "status": "created",
                "ticket_number": "TICKET-OTHER",
                "ticket_status": "Open",
                "error": None,
            },
        ]
    }

    combined_payload = ticket_http.put_calls[0]["json"]
    quota_change_requests = combined_payload["properties"]["quotaTicketDetails"][
        "quotaChangeRequests"
    ]
    assert len(quota_change_requests) == 2
    assert quota_change_requests[0]["region"] == "eastus"
    assert json.loads(quota_change_requests[0]["payload"]) == {
        "VMFamily": "DASv6 Series",
        "NewLimit": 4,
    }
    assert quota_change_requests[1]["region"] == "westus"
    assert json.loads(quota_change_requests[1]["payload"]) == {
        "VMFamily": "EASv6 Series",
        "NewLimit": 8,
    }

    received = [
        event["data"]
        for event in _events(log_path)
        if event["event_type"] == "support-ticket-received"
    ]
    assert [event["ticket_number"] for event in received] == ["TICKET-COMBINED", "TICKET-OTHER"]

