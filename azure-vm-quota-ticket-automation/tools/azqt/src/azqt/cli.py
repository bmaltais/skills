"""Command-line entry point for azqt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

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
from azqt.runstate.init_run import init_run, log_path_for_run
from azqt.skumapping.map_sku import SkuCandidate, load_batch_candidates, resolve_candidates
from azqt.validation import validate_field


def _print_json(payload: dict[str, Any]) -> None:
    """Print one JSON object for the host agent to consume."""

    print(json.dumps(payload))


def _stub(name: str) -> Callable[[argparse.Namespace], int]:
    def handler(_args: argparse.Namespace) -> int:
        _print_json({"todo": True, "subcommand": name})
        return 0

    return handler


def _handle_init_run(args: argparse.Namespace) -> int:
    result = init_run(args.document)
    _print_json({"run_id": result["run_id"], "log_path": str(result["log_path"])})
    return 0


def _handle_map_sku(args: argparse.Namespace) -> int:
    """Resolve one or more candidates and append one audit event per result."""

    direct_values_supplied = any(
        value is not None for value in (args.sku, args.vcpu, args.memory_gib)
    )
    if args.input:
        if direct_values_supplied:
            raise ValueError("--input cannot be combined with --sku, --vcpu, or --memory-gib.")
        candidates = load_batch_candidates(args.input)
    elif args.sku is not None:
        if args.vcpu is not None or args.memory_gib is not None:
            raise ValueError("--sku cannot be combined with --vcpu or --memory-gib.")
        candidates = [SkuCandidate(args.candidate_id, args.sku, None, None)]
    elif args.vcpu is not None or args.memory_gib is not None:
        if args.vcpu is None or args.memory_gib is None:
            raise ValueError("--vcpu and --memory-gib must be supplied together.")
        candidates = [SkuCandidate(args.candidate_id, None, float(args.vcpu), args.memory_gib)]
    else:
        raise ValueError("Provide --sku, --vcpu with --memory-gib, or --input.")

    logger = AuditLogger(log_path_for_run(args.run))
    resolutions: list[dict[str, Any]] = []
    for candidate, resolution in resolve_candidates(candidates):
        logger.log(
            "sku-resolution",
            {
                "candidate_id": candidate.candidate_id,
                "input": candidate.audit_input(),
                "outcome": resolution,
            },
        )
        resolutions.append(resolution)

    _print_json({"resolutions": resolutions})
    return 0


def _handle_validate(args: argparse.Namespace) -> int:
    """Validate a clarification answer and print its deterministic JSON result."""

    _print_json(validate_field(args.field, args.value).to_payload())
    return 0


_AGENT_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "candidate-extracted",
        "clarification-answer-applied",
        "candidate-excluded",
        "extraction-error",
    }
)


def _load_event_data(raw_data: str) -> dict[str, Any]:
    """Load a log-event JSON object from inline text or an ``@`` file reference."""

    if raw_data.startswith("@"):
        file_path = Path(raw_data[1:])
        try:
            raw_data = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"Unable to read --data file {file_path}: {exc}") from exc
        source = f"--data file {file_path}"
    else:
        source = "--data"

    try:
        data = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {source}: {exc.msg}.") from exc

    if not isinstance(data, dict):
        raise ValueError(f"JSON in {source} must be an object.")
    return data


def _handle_log_event(args: argparse.Namespace) -> int:
    """Append an agent-originated event to the run's shared audit log."""

    if args.type not in _AGENT_EVENT_TYPES:
        expected = ", ".join(sorted(_AGENT_EVENT_TYPES))
        raise ValueError(f"Unsupported event type {args.type!r}. Expected one of: {expected}.")

    data = _load_event_data(args.data)
    logger = AuditLogger(log_path_for_run(args.run))
    ok = logger.log(args.type, data)
    _print_json({"ok": ok, "write_failed": logger.write_failed})
    return 0


_FAILURE_OUTCOMES = frozenset({"failure", "timeout"})


def _read_audit_events(log_path: Path) -> list[dict[str, Any]]:
    """Read and validate the JSONL events for one run's audit log."""

    events: list[dict[str, Any]] = []
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"Unable to read audit log {log_path}: {exc}") from exc

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid audit JSONL at line {line_number}: {exc.msg}.") from exc
        if not isinstance(event, dict):
            raise ValueError(f"Invalid audit JSONL at line {line_number}: event must be an object.")
        if not isinstance(event.get("event_type"), str):
            raise ValueError(f"Invalid audit JSONL at line {line_number}: event_type must be a string.")
        if not isinstance(event.get("data"), dict):
            raise ValueError(f"Invalid audit JSONL at line {line_number}: data must be an object.")
        events.append(event)
    return events


def _group_key(data: Mapping[str, Any], event_index: int) -> tuple[str, tuple[tuple[str, str], ...] | None, int | None]:
    """Return a stable ticket identity, keeping malformed entries distinct.

    A ticket's identity is its subscription_id plus its full set of
    region/quota_family line items (order-independent), matching the
    ``_group_identity`` shape logged by ``submit-tickets``.
    """

    subscription_id = data.get("subscription_id")
    line_items = data.get("line_items")
    if (
        isinstance(subscription_id, str)
        and isinstance(line_items, list)
        and all(
            isinstance(item, Mapping)
            and isinstance(item.get("region"), str)
            and isinstance(item.get("quota_family"), str)
            for item in line_items
        )
    ):
        line_item_key = tuple(sorted((item["region"], item["quota_family"]) for item in line_items))
        return subscription_id, line_item_key, None
    return "", None, event_index


def _finish_run_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Tally final outcomes from persisted audit events only."""

    GroupKey = tuple[str, tuple[tuple[str, str], ...] | None, int | None]
    created_groups: set[GroupKey] = set()
    failed_groups: dict[GroupKey, dict[str, Any]] = {}
    candidates_excluded: list[dict[str, Any]] = []
    stop_reasons: list[dict[str, Any]] = []
    created = 0

    for event_index, event in enumerate(events):
        event_type = event["event_type"]
        data = dict(event["data"])
        group_key = _group_key(data, event_index)

        if event_type == "support-ticket-received":
            created += 1
            created_groups.add(group_key)
        elif event_type == "quota-request-group-excluded":
            failed_groups[group_key] = data
        elif (
            event_type == "submission-outcome"
            and data.get("outcome") in _FAILURE_OUTCOMES
        ):
            failed_groups[group_key] = data
        elif event_type == "candidate-excluded":
            candidates_excluded.append(data)
        elif event_type == "extraction-error":
            stop_reasons.append(data)

    groups_failed = [
        data for group_key, data in failed_groups.items() if group_key not in created_groups
    ]
    return {
        "created": created,
        "failed": len(groups_failed),
        "excluded": len(candidates_excluded),
        "groups_failed": groups_failed,
        "candidates_excluded": candidates_excluded,
        "stopped_early": bool(stop_reasons),
        "stop_reasons": stop_reasons,
    }


def _handle_finish_run(args: argparse.Namespace) -> int:
    """Report persisted run outcomes and append exactly one final audit entry."""

    log_path = log_path_for_run(args.run)
    events = _read_audit_events(log_path)
    summary = _finish_run_summary(events)
    if not any(event["event_type"] == "run-end" for event in events):
        AuditLogger(log_path).log(
            "run-end",
            {
                "created": summary["created"],
                "failed": summary["failed"],
                "excluded": summary["excluded"],
            },
        )

    _print_json(summary)
    return 1 if summary["failed"] or summary["excluded"] or summary["stopped_early"] else 0


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


def _handle_submit_tickets(args: argparse.Namespace) -> int:
    """Group, authenticate, submit, audit, and report confirmed quota requests."""

    requests = _load_confirmed_requests(args.input)
    mapper = PayloadMapper()
    groups = mapper.group(requests)
    logger = AuditLogger(log_path_for_run(args.run))
    for group in groups:
        logger.log(
            "quota-request-group",
            {**_group_identity(group), "candidate_ids": [request.candidate_id for request in group.requests]},
        )

    if not groups:
        _print_json({"results": []})
        return 0

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

    classification_ids = ProblemClassificationCache().resolve(args.run, initial_token.reveal())
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

    _print_json({"results": [result for result in results if result is not None]})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="azqt",
        description="Azure Quota Ticket CLI - deterministic backend for the "
        "azure-vm-quota-ticket-automation skill.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    init_run_parser = subparsers.add_parser(
        "init-run", help="Start a Run: generate a run id and audit log file."
    )
    init_run_parser.add_argument("--document", required=True, help="Path to the Quota_Request_Document.")
    init_run_parser.set_defaults(handler=_handle_init_run)

    map_sku = subparsers.add_parser(
        "map-sku", help="Resolve VM SKU name(s) or informal size(s) to a Compute_Quota_Family."
    )
    map_sku.add_argument("--run", required=True, help="Run id from init-run.")
    map_sku.add_argument(
        "--candidate-id",
        default="single",
        help="Candidate identifier for a single-item --sku or --vcpu invocation.",
    )
    map_sku.add_argument("--sku", help="A single formal VM SKU name.")
    map_sku.add_argument("--vcpu", type=int, help="vCPU count of an informal size description.")
    map_sku.add_argument(
        "--memory-gib", type=float, help="Memory amount (GiB) of an informal size description."
    )
    map_sku.add_argument(
        "--input", help="Path to a candidates.json file for batch resolution."
    )
    map_sku.set_defaults(handler=_handle_map_sku)

    validate = subparsers.add_parser(
        "validate", help="Deterministic format/enum validation for a single field value."
    )
    validate.add_argument("--run", required=True, help="Run id from init-run.")
    validate.add_argument("--field", required=True, help="Field name to validate.")
    validate.add_argument("--value", required=True, help="Value to validate.")
    validate.add_argument("--candidate-id", help="Candidate_Quota_Request identifier, if applicable.")
    validate.set_defaults(handler=_handle_validate)

    log_event = subparsers.add_parser(
        "log-event", help="Append an agent-originated event to the run's shared audit log."
    )
    log_event.add_argument("--run", required=True, help="Run id from init-run.")
    log_event.add_argument("--type", required=True, help="Event type.")
    log_event.add_argument(
        "--data", required=True, help="Inline JSON, or @path/to/file.json to read JSON from a file."
    )
    log_event.set_defaults(handler=_handle_log_event)

    submit_tickets = subparsers.add_parser(
        "submit-tickets", help="Group, build payloads for, authenticate, and submit Confirmed_Quota_Request objects."
    )
    submit_tickets.add_argument("--run", required=True, help="Run id from init-run.")
    submit_tickets.add_argument(
        "--input", required=True, help="Path to a confirmed_requests.json file."
    )
    submit_tickets.set_defaults(handler=_handle_submit_tickets)

    finish_run = subparsers.add_parser(
        "finish-run", help="Tally the run's audit log and report final counts/exit code."
    )
    finish_run.add_argument("--run", required=True, help="Run id from init-run.")
    finish_run.set_defaults(handler=_handle_finish_run)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args.handler
    try:
        return handler(args)
    except Exception as exc:  # noqa: BLE001 - top-level CLI error boundary
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
