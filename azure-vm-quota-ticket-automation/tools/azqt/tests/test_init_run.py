"""Unit tests for azqt.runstate.init_run.

**Validates: Requirements 9.1**
"""

from __future__ import annotations

import json
from pathlib import Path

from azqt.runstate.init_run import generate_run_id, init_run


def test_run_ids_are_unique_across_multiple_invocations(tmp_path: Path) -> None:
    """Repeated init_run calls (and raw id generation) never collide."""

    generated_ids = {generate_run_id() for _ in range(200)}
    assert len(generated_ids) == 200

    results = [init_run("document.txt", state_dir=tmp_path) for _ in range(10)]
    run_ids = [result["run_id"] for result in results]
    assert len(set(run_ids)) == len(run_ids)

    # Each run also gets its own distinct log file.
    log_paths = [result["log_path"] for result in results]
    assert len(set(log_paths)) == len(log_paths)


def test_init_run_creates_log_file_with_run_start_entry(tmp_path: Path) -> None:
    """The run-start entry records a timestamp and the document path."""

    document_path = tmp_path / "quota-request.txt"
    document_path.write_text("some request", encoding="utf-8")

    result = init_run(str(document_path), state_dir=tmp_path)

    log_path = result["log_path"]
    assert isinstance(log_path, Path)
    assert log_path.exists()
    assert result["write_failed"] is False

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["event_type"] == "run-start"
    assert "timestamp" in entry and entry["timestamp"]
    assert entry["data"]["run_id"] == result["run_id"]
    assert entry["data"]["document_path"] == str(document_path)


def test_init_run_returns_run_id_and_log_path_under_given_state_dir(tmp_path: Path) -> None:
    """The log file lives inside the injected state_dir, named after the run id."""

    result = init_run("doc.txt", state_dir=tmp_path)

    assert result["run_id"]
    log_path = result["log_path"]
    assert log_path.parent == tmp_path
    assert log_path.name == f"{result['run_id']}.jsonl"


def test_init_run_creates_state_dir_when_missing(tmp_path: Path) -> None:
    """A non-existent state_dir (e.g. first run ever) is created rather than erroring."""

    nested_state_dir = tmp_path / "does" / "not" / "exist-yet"
    assert not nested_state_dir.exists()

    result = init_run("doc.txt", state_dir=nested_state_dir)

    assert nested_state_dir.exists()
    assert result["log_path"].exists()
