"""CLI tests for ``azqt log-event``.

**Validates: Requirements 9.2, 9.4**
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from azqt.cli import main
from azqt.runstate.init_run import init_run


EVENT_TYPES = (
    "candidate-extracted",
    "clarification-answer-applied",
    "candidate-excluded",
    "extraction-error",
)


def _start_run(tmp_path: Path) -> tuple[str, Path]:
    run = init_run("quota-request.txt", state_dir=tmp_path)
    return run["run_id"], run["log_path"]


@pytest.mark.parametrize("event_type", EVENT_TYPES)
def test_log_event_round_trips_each_supported_type_from_inline_json(
    event_type: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each agent event type is persisted with its unmodified JSON-object data."""

    monkeypatch.setenv("AZQT_STATE_DIR", str(tmp_path))
    run_id, log_path = _start_run(tmp_path)
    data = {"candidate_id": f"candidate-for-{event_type}", "source": "inline"}

    exit_code = main(
        ["log-event", "--run", run_id, "--type", event_type, "--data", json.dumps(data)]
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True, "write_failed": False}
    entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert entries[-1]["event_type"] == event_type
    assert entries[-1]["data"] == data


def test_log_event_reads_json_object_from_at_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The ``@file`` input form loads an event payload before appending it."""

    monkeypatch.setenv("AZQT_STATE_DIR", str(tmp_path))
    run_id, log_path = _start_run(tmp_path)
    data_path = tmp_path / "candidate.json"
    data = {"candidate_id": "file-candidate", "completeness_state": "Complete"}
    data_path.write_text(json.dumps(data), encoding="utf-8")

    exit_code = main(
        [
            "log-event",
            "--run",
            run_id,
            "--type",
            "candidate-extracted",
            "--data",
            f"@{data_path}",
        ]
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True, "write_failed": False}
    entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert entries[-1]["event_type"] == "candidate-extracted"
    assert entries[-1]["data"] == data


@pytest.mark.parametrize(
    ("raw_data", "setup_file"),
    [
        ("{not-json}", False),
        ("@malformed.json", True),
    ],
)
def test_log_event_rejects_malformed_data_without_partial_write(
    raw_data: str,
    setup_file: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Invalid inline or file JSON has a clear non-zero error and adds no event."""

    monkeypatch.setenv("AZQT_STATE_DIR", str(tmp_path))
    run_id, log_path = _start_run(tmp_path)
    if setup_file:
        malformed_path = tmp_path / "malformed.json"
        malformed_path.write_text("{not-json}", encoding="utf-8")
        raw_data = f"@{malformed_path}"

    before = log_path.read_text(encoding="utf-8")
    exit_code = main(
        [
            "log-event",
            "--run",
            run_id,
            "--type",
            "candidate-extracted",
            "--data",
            raw_data,
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "Invalid JSON" in captured.err
    assert log_path.read_text(encoding="utf-8") == before
