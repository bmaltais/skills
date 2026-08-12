"""Group, authenticate, submit, audit, and report confirmed quota requests.

This module is the deep implementation behind ``azqt submit-tickets``: the CLI
only parses arguments and calls :func:`run_submit_tickets`. Every dependency
(auth, classification cache, retry policy, ticket client, audit log) is wired
up here so callers and tests only need to know one entry point.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from azqt.audit.logger import AuditLogger
from azqt.azure.auth import AuthRenewalError, AzureAuthProvider
from azqt.azure.payload_mapper import (
    ConfirmedQuotaRequest,
    PayloadMapper,
    SubscriptionTicketGroup,
)
from azqt.azure.problem_classification_cache import ProblemClassificationCache
from azqt.azure.retry import RetryHandler
from azqt.azure.ticket_client import TicketClient, TicketSubmissionResult
from azqt.runstate.init_run import log_path_for_run


def _load_confirmed_requests(input_path: str) -> list[ConfirmedQuotaRequest]:
    """Parse the agent-authored confirmed-request array before contacting Azure."""

    path = Path(input_path)
    try:
        raw_requests = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Unable to read --input file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in --input file {path}: {exc.msg}.") from exc

    if not isinstance(raw_requests, list):
        raise ValueError("confirmed_requests.json must contain a JSON array.")
    if not all(isinstance(request, Mapping) for request in raw_requests):
        raise ValueError("Each confirmed request must be a JSON object.")
    return [ConfirmedQuotaRequest.from_mapping(request) for request in raw_requests]


def _group_identity(group: SubscriptionTicketGroup) -> dict[str, Any]:
    return {
        "subscription_id": group.subscription_id,
        "line_items": [
            {"region": line_item.region, "quota_family": line_item.quota_family}
            for line_item in group.line_items
        ],
    }


def _audit_group_outcome(
    logger: AuditLogger,
    group: SubscriptionTicketGroup,
    *,
    action: str,
    outcome: str,
    error: str | None = None,
) -> None:
    data: dict[str, Any] = {**_group_identity(group), "action": action, "outcome": outcome}
    if error is not None:
        data["error"] = error
    logger.log("submission-outcome", data)


def _result_payload(
    group: SubscriptionTicketGroup,
    result: TicketSubmissionResult | None = None,
    *,
    error: str | None = None,
) -> dict[str, Any]:
    if result is not None and result.succeeded:
        status = "created"
        ticket_number = result.ticket_number
        ticket_status = result.ticket_status
        result_error = None
    else:
        status = "failed"
        ticket_number = None
        ticket_status = None
        result_error = error if error is not None else result.error if result is not None else None
    return {
        "group_key": _group_identity(group),
        "status": status,
        "ticket_number": ticket_number,
        "ticket_status": ticket_status,
        "error": result_error,
    }


def run_submit_tickets(input_path: str, run_id: str) -> dict[str, Any]:
    """Run the full submit-tickets flow and return the CLI's JSON payload."""

    requests = _load_confirmed_requests(input_path)
    mapper = PayloadMapper()
    groups = mapper.group(requests)
    logger = AuditLogger(log_path_for_run(run_id))
    for group in groups:
        logger.log(
            "quota-request-group",
            {**_group_identity(group), "candidate_ids": [request.candidate_id for request in group.requests]},
        )

    if not groups:
        return {"results": []}

    try:
        auth = AzureAuthProvider()
        initial_token = auth.get_access_token()
    except Exception as exc:
        for group in groups:
            _audit_group_outcome(
                logger,
                group,
                action="access-token-request",
                outcome="failure",
                error=str(exc),
            )
        raise
    for group in groups:
        _audit_group_outcome(
            logger, group, action="access-token-request", outcome="success"
        )

    classification_ids = ProblemClassificationCache().resolve(run_id, initial_token.reveal())
    mapped_groups = mapper.map_groups(groups, classification_ids)
    results: list[dict[str, Any] | None] = [None] * len(mapped_groups)
    for index, mapped in enumerate(mapped_groups):
        if mapped.succeeded:
            continue
        assert mapped.error is not None
        error = str(mapped.error)
        results[index] = _result_payload(mapped.group, error=error)
        logger.log(
            "quota-request-group-excluded",
            {
                **_group_identity(mapped.group),
                "candidate_ids": [request.candidate_id for request in mapped.group.requests],
                "reason": error,
            },
        )

    active_group: SubscriptionTicketGroup | None = None

    def record_ticket_action(action: str, outcome: str, error: str | None) -> None:
        if active_group is not None:
            _audit_group_outcome(
                logger, active_group, action=action, outcome=outcome, error=error
            )

    client = TicketClient(
        retry_handler=RetryHandler(audit_logger=logger),
        action_outcome_callback=record_ticket_action,
    )
    for index, mapped in enumerate(mapped_groups):
        if not mapped.succeeded:
            continue
        active_group = mapped.group
        try:
            access_token = auth.get_access_token()
        except AuthRenewalError as exc:
            error = str(exc)
            for pending_index in range(index, len(mapped_groups)):
                if results[pending_index] is not None:
                    continue
                pending_group = mapped_groups[pending_index].group
                results[pending_index] = _result_payload(pending_group, error=error)
                _audit_group_outcome(
                    logger,
                    pending_group,
                    action="access-token-renewal",
                    outcome="failure",
                    error=error,
                )
            break

        _audit_group_outcome(logger, active_group, action="access-token", outcome="success")
        try:
            submission = client.submit(active_group, mapped.payload or {}, access_token.reveal())
        except Exception as exc:  # pragma: no cover - defensive group isolation boundary
            error = f"Ticket submission failed unexpectedly: {exc}"
            submission = None
        if submission is None:
            results[index] = _result_payload(active_group, error=error)
            _audit_group_outcome(
                logger, active_group, action="ticket-creation", outcome="failure", error=error
            )
            continue

        results[index] = _result_payload(active_group, submission)
        if submission.succeeded:
            logger.log(
                "support-ticket-received",
                {
                    **_group_identity(active_group),
                    "ticket_number": submission.ticket_number,
                    "ticket_status": submission.ticket_status,
                },
            )

    return {"results": [result for result in results if result is not None]}
