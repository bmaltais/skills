"""Unit tests for azqt.audit.logger.

**Validates: Requirements 9.1, 9.7, 9.9, 9.11**
"""

from __future__ import annotations

import json
from pathlib import Path

from azqt.audit.logger import AuditLogger, SENSITIVE_KEYS


def test_append_only_ordering_preserves_write_order(tmp_path: Path) -> None:
    """Multiple sequential writes land as ordered, individually-valid JSON lines."""

    log_path = tmp_path / "run.jsonl"
    logger = AuditLogger(log_path)

    for index in range(5):
        ok = logger.log("test-event", {"sequence": index})
        assert ok is True
        assert logger.write_failed is False

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5

    for index, line in enumerate(lines):
        parsed = json.loads(line)  # raises if not valid JSON
        assert parsed["event_type"] == "test-event"
        assert parsed["data"]["sequence"] == index


def test_append_only_preserves_earlier_writes_across_logger_instances(tmp_path: Path) -> None:
    """Re-opening the same log path with a new AuditLogger never truncates it."""

    log_path = tmp_path / "run.jsonl"
    first_logger = AuditLogger(log_path)
    first_logger.log("first-event", {"value": "a"})

    second_logger = AuditLogger(log_path)
    second_logger.log("second-event", {"value": "b"})

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event_type"] == "first-event"
    assert json.loads(lines[1])["event_type"] == "second-event"


def test_redaction_hides_sensitive_keys_including_nested(tmp_path: Path) -> None:
    """SENSITIVE_KEYS values, top-level and nested, never appear in the file content."""

    log_path = tmp_path / "run.jsonl"
    logger = AuditLogger(log_path)

    fake_secret = "super-secret-value-should-not-leak"
    fake_token = "fake-access-token-should-not-leak"
    fake_cert = "fake-certificate-contents-should-not-leak"

    data = {
        "client_secret": fake_secret,
        "preserved_field": "keep-me",
        "nested": {
            "access_token": fake_token,
            "still_preserved": "keep-me-too",
            "deeper": {"certificate": fake_cert},
        },
        "list_field": [
            {"access_token": fake_token},
            "plain-string",
        ],
    }

    ok = logger.log("auth-event", data)
    assert ok is True

    raw_content = log_path.read_text(encoding="utf-8")

    for secret_value in (fake_secret, fake_token, fake_cert):
        assert secret_value not in raw_content

    parsed = json.loads(raw_content.splitlines()[0])
    assert parsed["data"]["preserved_field"] == "keep-me"
    assert parsed["data"]["nested"]["still_preserved"] == "keep-me-too"
    assert parsed["data"]["client_secret"] != fake_secret
    assert parsed["data"]["nested"]["access_token"] != fake_token
    assert parsed["data"]["nested"]["deeper"]["certificate"] != fake_cert
    assert parsed["data"]["list_field"][0]["access_token"] != fake_token
    assert parsed["data"]["list_field"][1] == "plain-string"

    # Sanity check that SENSITIVE_KEYS covers the keys this test relies on.
    assert {"client_secret", "certificate", "access_token"} <= SENSITIVE_KEYS


def test_log_does_not_raise_and_reports_write_failed_for_missing_directory(
    tmp_path: Path,
) -> None:
    """A log path inside a non-existent directory is a best-effort failure, not a raise."""

    unwritable_path = tmp_path / "does-not-exist" / "run.jsonl"
    logger = AuditLogger(unwritable_path)

    ok = logger.log("test-event", {"sequence": 0})

    assert ok is False
    assert logger.write_failed is True
    assert not unwritable_path.exists()


def test_log_does_not_raise_and_reports_write_failed_for_directory_path(
    tmp_path: Path,
) -> None:
    """Pointing the logger at a directory (instead of a file) fails without raising."""

    directory_path = tmp_path / "a-directory"
    directory_path.mkdir()
    logger = AuditLogger(directory_path)

    ok = logger.log("test-event", {"sequence": 0})

    assert ok is False
    assert logger.write_failed is True


def test_write_failed_resets_to_false_after_a_subsequent_successful_write(
    tmp_path: Path,
) -> None:
    """write_failed reflects only the most recent log() call."""

    unwritable_path = tmp_path / "missing-dir" / "run.jsonl"
    logger = AuditLogger(unwritable_path)
    assert logger.log("bad", {}) is False
    assert logger.write_failed is True

    logger.log_path = tmp_path / "run.jsonl"
    assert logger.log("good", {}) is True
    assert logger.write_failed is False
