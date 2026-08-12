"""Deterministic clarification-field validation and refusal detection.

The host agent uses this module through ``azqt validate`` before accepting a
clarification answer. Validation is intentionally limited to the fields whose
mechanical rules are defined in Requirements 3.5 and 3.10.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

# This pragmatic RFC 5322-compatible pattern supports dot-atoms and quoted
# local parts, standard DNS host names, and bracketed IPv4 literals. It avoids
# accepting whitespace, malformed dot-atoms, or malformed domain labels.
_EMAIL_PATTERN = re.compile(
    r"^(?:[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0B\x0C\x0E-\x1F\x20\x21\x23-\x5B\x5D-\x7E]|\\[\x01-\x09\x0B\x0C\x0E-\x7F])*\")@(?:(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\])$"
)
_UUID_PATTERN = re.compile(
    r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$"
)
_POSITIVE_INTEGER_PATTERN = re.compile(r"^[0-9]+$")

DEFAULT_REFUSAL_PHRASES: tuple[str, ...] = (
    "unknown",
    "n/a",
    "don't know",
    "won't provide",
    "not available",
)
_VALID_SEVERITY_LEVELS: frozenset[str] = frozenset({"minimal", "moderate", "critical"})


@dataclass(frozen=True)
class ValidationResult:
    """The deterministic outcome for one clarification-field answer."""

    valid: bool
    reason: str
    refusal: bool = False

    def to_payload(self) -> dict[str, bool | str]:
        """Return the JSON object emitted by the ``validate`` subcommand."""

        payload: dict[str, bool | str] = {"valid": self.valid, "reason": self.reason}
        if self.refusal:
            payload["refusal"] = True
        return payload


def _normalise_for_phrase_match(value: str) -> str:
    """Case-fold and collapse whitespace before matching refusal phrases."""

    return " ".join(value.casefold().split())


def detect_refusal(
    value: str, *, refusal_phrases: Sequence[str] = DEFAULT_REFUSAL_PHRASES
) -> str | None:
    """Return the first configured refusal phrase found in ``value``.

    Matching is case-insensitive and works within a natural-language response,
    allowing answers such as ``"Sorry, I don't know that value"``. Callers can
    supply a different phrase sequence without changing validator logic.
    """

    normalised_value = _normalise_for_phrase_match(value)
    for phrase in refusal_phrases:
        normalised_phrase = _normalise_for_phrase_match(phrase)
        if normalised_phrase and normalised_phrase in normalised_value:
            return phrase
    return None


def validate_field(
    field: str,
    value: str,
    *,
    refusal_phrases: Sequence[str] = DEFAULT_REFUSAL_PHRASES,
) -> ValidationResult:
    """Validate one supported field value or flag an explicit refusal.

    Refusal detection runs first because an explicit refusal must cause the
    associated candidate to be excluded immediately, independent of the
    requested field's normal format rule (Requirement 3.10).
    """

    refusal_phrase = detect_refusal(value, refusal_phrases=refusal_phrases)
    if refusal_phrase is not None:
        return ValidationResult(
            valid=False,
            refusal=True,
            reason=f"matched refusal phrase '{refusal_phrase}'",
        )

    if field == "ContactEmail":
        if _EMAIL_PATTERN.fullmatch(value):
            return ValidationResult(valid=True, reason="valid")
        return ValidationResult(valid=False, reason="not a valid email address")

    if field == "SubscriptionId":
        if _UUID_PATTERN.fullmatch(value):
            return ValidationResult(valid=True, reason="valid")
        return ValidationResult(valid=False, reason="not a UUID")

    if field == "RequestedQuota":
        if _POSITIVE_INTEGER_PATTERN.fullmatch(value) and int(value) > 0:
            return ValidationResult(valid=True, reason="valid")
        return ValidationResult(valid=False, reason="not a positive integer")

    if field == "SeverityLevel":
        if value in _VALID_SEVERITY_LEVELS:
            return ValidationResult(valid=True, reason="valid")
        return ValidationResult(
            valid=False,
            reason="must be one of: minimal, moderate, critical",
        )

    return ValidationResult(valid=False, reason=f"unsupported field '{field}'")
