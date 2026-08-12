"""CLI tests for ``azqt validate``.

**Validates: Requirements 3.5, 3.10**
"""

from __future__ import annotations

import json

from azqt.cli import main


def test_validate_prints_a_valid_field_result(capsys) -> None:
    """A supported field with a compliant value prints the required JSON result."""

    exit_code = main(
        [
            "validate",
            "--run",
            "not-used-by-validation",
            "--field",
            "SubscriptionId",
            "--value",
            "64080835-75bb-4085-aa73-e802ad5f3a04",
        ]
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {"valid": True, "reason": "valid"}


def test_validate_prints_an_invalid_field_result(capsys) -> None:
    """An invalid ordinary answer is not marked as an explicit refusal."""

    exit_code = main(
        [
            "validate",
            "--run",
            "not-used-by-validation",
            "--field",
            "RequestedQuota",
            "--value",
            "0",
        ]
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "valid": False,
        "reason": "not a positive integer",
    }


def test_validate_prints_a_refusal_result(capsys) -> None:
    """An explicit refusal carries the required refusal flag and match reason."""

    exit_code = main(
        [
            "validate",
            "--run",
            "not-used-by-validation",
            "--field",
            "ContactEmail",
            "--value",
            "I won't provide it",
            "--candidate-id",
            "candidate-7",
        ]
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "valid": False,
        "refusal": True,
        "reason": "matched refusal phrase 'won't provide'",
    }
