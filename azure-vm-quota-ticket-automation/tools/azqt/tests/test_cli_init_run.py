"""CLI-level tests for the ``init-run`` subcommand.

**Validates: Requirements 9.1**
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from azqt.cli import main


def test_init_run_subcommand_prints_run_id_and_log_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`azqt init-run --document <path>` prints {"run_id": ..., "log_path": ...} and exits 0."""

    monkeypatch.setenv("AZQT_STATE_DIR", str(tmp_path))
    document_path = tmp_path / "doc.txt"
    document_path.write_text("hello", encoding="utf-8")

    exit_code = main(["init-run", "--document", str(document_path)])

    assert exit_code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())

    assert set(payload.keys()) == {"run_id", "log_path"}
    assert payload["run_id"]
    # log_path must be the native string form of a real Path, directly usable
    # in a later shell command on this OS.
    log_path = Path(payload["log_path"])
    assert log_path.exists()
    assert payload["log_path"] == str(log_path)
