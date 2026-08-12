"""CLI tests for ``azqt finish-run``.

**Validates: Requirements 8.4, 8.5, 8.6, 9.8**
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from azqt.cli import main


RUN_ID = "a" * 32


def _event(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": "2026-01-01T00:00:00+00:00",
        "event_type": event_type,
        "data": data,
    }


def _write_audit_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    events: list[dict[str, Any]],
) -> Path:
    """Create a run-owned JSONL log without using the runtime logger."""

    monkeypatch.setenv("AZQT_STATE_DIR", str(tmp_path))
    log_path = tmp_path / f"{RUN_ID}.jsonl"
    log_path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8"
    )
    return log_path


def _read_events(log_path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]


def test_finish_run_returns_zero_and_summary_for_all_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A received ticket with no failures or exclusions is a successful run."""

    ticket = {
        "subscription_id": "sub-success",
        "line_items": [{"region": "eastus", "quota_family": "standardDSv5Family"}],
        "ticket_number": "TICKET-1",
        "ticket_status": "Open",
    }
    log_path = _write_audit_fixture(
        tmp_path,
        monkeypatch,
        [_event("run-start", {"run_id": RUN_ID}), _event("support-ticket-received", ticket)],
    )

    exit_code = main(["finish-run", "--run", RUN_ID])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "created": 1,
        "failed": 0,
        "excluded": 0,
        "groups_failed": [],
        "candidates_excluded": [],
        "stopped_early": False,
        "stop_reasons": [],
    }
    assert _read_events(log_path)[-1]["event_type"] == "run-end"


def test_finish_run_returns_nonzero_and_lists_failed_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failed submission outcome makes the final run status non-zero."""

    failed_group = {
        "subscription_id": "sub-failure",
        "line_items": [{"region": "eastus", "quota_family": "standardDSv5Family"}],
        "action": "ticket-creation",
        "outcome": "failure",
        "error": "HTTP 400: invalid quota request",
    }
    _write_audit_fixture(tmp_path, monkeypatch, [_event("submission-outcome", failed_group)])

    exit_code = main(["finish-run", "--run", RUN_ID])

    assert exit_code != 0
    assert json.loads(capsys.readouterr().out) == {
        "created": 0,
        "failed": 1,
        "excluded": 0,
        "groups_failed": [failed_group],
        "candidates_excluded": [],
        "stopped_early": False,
        "stop_reasons": [],
    }


def test_finish_run_returns_nonzero_for_exclusion_without_group_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A pre-submission candidate exclusion alone makes the run incomplete."""

    excluded_candidate = {
        "candidate_id": "candidate-1",
        "subscription_id": "sub-excluded",
        "region": "eastus",
        "vm_sku_name": "Standard_D2s_v5",
        "reason": "clarification rounds exhausted",
    }
    _write_audit_fixture(tmp_path, monkeypatch, [_event("candidate-excluded", excluded_candidate)])

    exit_code = main(["finish-run", "--run", RUN_ID])

    assert exit_code != 0
    assert json.loads(capsys.readouterr().out) == {
        "created": 0,
        "failed": 0,
        "excluded": 1,
        "groups_failed": [],
        "candidates_excluded": [excluded_candidate],
        "stopped_early": False,
        "stop_reasons": [],
    }


def test_finish_run_appends_run_end_exactly_once_across_repeated_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Repeated finalization reuses the persisted tally without duplicate run-end events."""

    log_path = _write_audit_fixture(tmp_path, monkeypatch, [_event("run-start", {"run_id": RUN_ID})])

    assert main(["finish-run", "--run", RUN_ID]) == 0
    first_summary = json.loads(capsys.readouterr().out)
    assert main(["finish-run", "--run", RUN_ID]) == 0
    second_summary = json.loads(capsys.readouterr().out)

    assert second_summary == first_summary
    run_end_events = [event for event in _read_events(log_path) if event["event_type"] == "run-end"]
    assert len(run_end_events) == 1
    assert run_end_events[0]["data"] == {"created": 0, "failed": 0, "excluded": 0}


def test_finish_run_returns_nonzero_and_stop_reason_for_extraction_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An extraction stop is an incomplete run even without group failures."""

    stop_reason = {"reason": "zero candidates found"}
    _write_audit_fixture(tmp_path, monkeypatch, [_event("extraction-error", stop_reason)])

    exit_code = main(["finish-run", "--run", RUN_ID])

    assert exit_code != 0
    assert json.loads(capsys.readouterr().out) == {
        "created": 0,
        "failed": 0,
        "excluded": 0,
        "groups_failed": [],
        "candidates_excluded": [],
        "stopped_early": True,
        "stop_reasons": [stop_reason],
    }
