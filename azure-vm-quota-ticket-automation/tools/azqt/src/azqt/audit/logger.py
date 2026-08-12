"""Append-only, redacted JSONL audit logger for a single Run.

This module is the single writer every other ``azqt`` subcommand uses to
record what happened during a Run (Req 9.1-9.13). It intentionally keeps the
on-disk representation of an :class:`AuditEvent` minimal - a timestamp, an
event type, and a free-form ``data`` payload - so later subcommands
(``init-run``, ``map-sku``, ``log-event``, ``submit-tickets``,
``finish-run``) can each log whatever fields are relevant to their own event
types without needing a new logger method or a schema change here.

Design notes:

- The log file is opened in append mode with ``encoding="utf-8"`` and
  ``newline="\\n"`` so the file's line structure (a single ``\\n`` per line,
  no ``\\r``) is byte-identical on Windows and POSIX (Req 9.9, Cross-Platform
  Considerations in design.md). The file is never opened in a truncating
  mode.
- Every write is flushed immediately so a log entry is durable on disk as
  soon as :meth:`AuditLogger.log` returns, rather than sitting in an
  in-process buffer (Req 9.9).
- Redaction of ``SENSITIVE_KEYS`` happens inside :meth:`AuditEvent.to_json_line`
  - i.e. inside serialization itself - so every call site gets it for free
  and cannot forget to redact before logging (Req 9.7, 5.8). Redaction
  recurses into nested dicts and lists within the event's ``data`` payload.
- A write failure (unwritable path, permission error, disk error, etc.) is
  caught inside :meth:`AuditLogger.log` and never propagates to the caller.
  The outcome of that specific call is reported both via the method's
  return value and via the ``write_failed`` attribute on the logger
  instance, which reflects only the most recent call (Req 9.11).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Keys whose values must never appear verbatim in the audit log, wherever
# they occur (top-level or nested) within an AuditEvent's data payload.
SENSITIVE_KEYS: frozenset[str] = frozenset({"client_secret", "certificate", "access_token"})

_REDACTED_PLACEHOLDER = "***REDACTED***"


def _redact(value: Any) -> Any:
    """Recursively redact SENSITIVE_KEYS anywhere within a JSON-like value.

    Dicts have any key found in SENSITIVE_KEYS replaced with a redaction
    placeholder (its value, however deeply nested, is never inspected or
    copied into the output). Lists are redacted element-wise. Every other
    value (str, int, float, bool, None) is returned unchanged.
    """

    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, val in value.items():
            if key in SENSITIVE_KEYS:
                redacted[key] = _REDACTED_PLACEHOLDER
            else:
                redacted[key] = _redact(val)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


@dataclass
class AuditEvent:
    """A single audit log entry.

    ``timestamp`` defaults to the current UTC time in ISO 8601 form if not
    supplied explicitly (mainly useful for tests that want a fixed value).
    ``data`` is an arbitrary JSON-serializable payload whose shape is
    entirely up to the caller/event type.
    """

    event_type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_json_line(self) -> str:
        """Serialize this event to a single JSON line, redacting secrets.

        Redaction is applied here - inside serialization - rather than
        requiring every call site to pre-redact its own payload.
        """

        payload = {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "data": _redact(self.data),
        }
        return json.dumps(payload, sort_keys=False)


class AuditLogger:
    """Append-only JSONL writer for a single Run's audit log file."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = Path(log_path)
        # Reflects only the outcome of the most recent log() call.
        self.write_failed: bool = False

    def log(self, event_type: str, data: dict[str, Any] | None = None) -> bool:
        """Append one AuditEvent to the log file.

        Returns True on success, False on failure. Never raises: any
        exception encountered while opening or writing the file is caught
        and reported only through the return value and the ``write_failed``
        attribute, per the best-effort write semantics required of the
        Audit_Logger (Req 9.11).
        """

        event = AuditEvent(event_type=event_type, data=data or {})
        line = event.to_json_line()
        try:
            with self.log_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")
                handle.flush()
        except OSError:
            self.write_failed = True
            return False
        else:
            self.write_failed = False
            return True
