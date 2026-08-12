"""Unit tests for clarification-field validation.

**Validates: Requirements 3.5, 3.10**
"""

from __future__ import annotations

import pytest

from azqt.validation import detect_refusal, validate_field


@pytest.mark.parametrize(
    ("value", "expected_valid"),
    [
        ("maxime.seguin@example.ca", True),
        ('"Maxime Seguin"@example.ca', True),
        ("maxime.seguin.example.ca", False),
        ("maxime@example", False),
        ("maxime @example.ca", False),
    ],
)
def test_contact_email_validation(value: str, expected_valid: bool) -> None:
    """ContactEmail accepts RFC 5322-compatible syntax and rejects malformed values."""

    assert validate_field("ContactEmail", value).valid is expected_valid


@pytest.mark.parametrize(
    ("value", "expected_valid"),
    [
        ("64080835-75bb-4085-aa73-e802ad5f3a04", True),
        ("64080835-75BB-4085-AA73-E802AD5F3A04", True),
        ("64080835-75bb-4085-aa73-e802ad5f3a0", False),
        ("not-a-subscription-id", False),
    ],
)
def test_subscription_id_validation(value: str, expected_valid: bool) -> None:
    """SubscriptionId must use canonical UUID formatting."""

    assert validate_field("SubscriptionId", value).valid is expected_valid


@pytest.mark.parametrize(
    ("value", "expected_valid"),
    [
        ("1", True),
        ("0008", True),
        ("0", False),
        ("-1", False),
        ("8.5", False),
        ("eight", False),
    ],
)
def test_requested_quota_validation(value: str, expected_valid: bool) -> None:
    """RequestedQuota accepts positive decimal integers only."""

    assert validate_field("RequestedQuota", value).valid is expected_valid


@pytest.mark.parametrize("value", ["minimal", "moderate", "critical"])
def test_severity_level_accepts_supported_values(value: str) -> None:
    """Every defined severity is accepted exactly as specified."""

    assert validate_field("SeverityLevel", value).valid is True


@pytest.mark.parametrize("value", ["high", "Moderate", "", "critical "])
def test_severity_level_rejects_other_values(value: str) -> None:
    """Values outside the accepted severity enum are invalid."""

    assert validate_field("SeverityLevel", value).valid is False


@pytest.mark.parametrize(
    ("value", "phrase"),
    [
        ("UNKNOWN", "unknown"),
        ("N/A", "n/a"),
        ("Sorry, I don't know the subscription.", "don't know"),
        ("I won't provide my email address.", "won't provide"),
        ("The requested quota is not available.", "not available"),
    ],
)
def test_refusal_detection_is_case_insensitive_and_handles_natural_language(
    value: str, phrase: str
) -> None:
    """Configured refusal phrases are identified in varied response phrasings."""

    result = validate_field("RequestedQuota", value)

    assert detect_refusal(value) == phrase
    assert result.valid is False
    assert result.refusal is True
    assert result.reason == f"matched refusal phrase '{phrase}'"


def test_refusal_phrase_list_is_configurable() -> None:
    """Callers can substitute a phrase list without changing validation code."""

    assert detect_refusal("decline", refusal_phrases=("decline",)) == "decline"
    assert detect_refusal("unknown", refusal_phrases=("decline",)) is None


def test_unknown_field_is_reported_as_invalid() -> None:
    """Unsupported field names produce a deterministic invalid result."""

    result = validate_field("Region", "canadacentral")

    assert result.valid is False
    assert result.refusal is False
    assert result.reason == "unsupported field 'Region'"
