"""Unit tests for service-principal Azure AD authentication.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8**
"""

from __future__ import annotations

import subprocess
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from azqt.azure.auth import (
    ARM_USE_CLI_ENV,
    AZURE_CLIENT_CERTIFICATE_ENV,
    AZURE_CLIENT_ID_ENV,
    AZURE_CLIENT_SECRET_ENV,
    AZURE_TENANT_ID_ENV,
    AccessToken,
    AuthConfigurationError,
    AuthRejectedError,
    AuthRenewalError,
    AuthTimeoutError,
    AzureAuthProvider,
    RedactedValue,
)


class FakeConfidentialClient:
    """In-process AAD substitute that records scopes without performing I/O."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = iter(responses)
        self.scopes: list[tuple[str, ...]] = []

    def acquire_token_for_client(self, *, scopes: tuple[str, ...]) -> dict[str, Any]:
        self.scopes.append(tuple(scopes))
        response = next(self.responses)
        if isinstance(response, BaseException):
            raise response
        if callable(response):
            return response()
        return response


def _set_valid_secret_credentials(monkeypatch: pytest.MonkeyPatch, secret: str) -> None:
    monkeypatch.setenv(AZURE_TENANT_ID_ENV, "tenant-id")
    monkeypatch.setenv(AZURE_CLIENT_ID_ENV, "client-id")
    monkeypatch.setenv(AZURE_CLIENT_SECRET_ENV, secret)
    monkeypatch.delenv(AZURE_CLIENT_CERTIFICATE_ENV, raising=False)


def _provider(
    client: FakeConfidentialClient,
    *,
    clock=lambda: datetime.now(timezone.utc),
    timeout_seconds: float = 0.1,
) -> AzureAuthProvider:
    return AzureAuthProvider(
        application_factory=lambda **_kwargs: client,
        clock=clock,
        timeout_seconds=timeout_seconds,
    )


def test_missing_credential_component_fails_before_msal_is_constructed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Required service-principal values are validated before any AAD-capable object exists."""

    for name in (
        AZURE_TENANT_ID_ENV,
        AZURE_CLIENT_ID_ENV,
        AZURE_CLIENT_SECRET_ENV,
        AZURE_CLIENT_CERTIFICATE_ENV,
    ):
        monkeypatch.delenv(name, raising=False)

    factory_called = False

    def factory(**_kwargs: Any) -> FakeConfidentialClient:
        nonlocal factory_called
        factory_called = True
        return FakeConfidentialClient([])

    with pytest.raises(AuthConfigurationError, match="tenant ID.*client ID.*client secret or certificate"):
        AzureAuthProvider(application_factory=factory)

    assert factory_called is False


def test_certificate_is_preferred_when_both_credential_forms_are_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Certificate authentication deliberately disregards a simultaneously configured secret."""

    _set_valid_secret_credentials(monkeypatch, "secret-that-must-not-be-selected")
    monkeypatch.setenv(AZURE_CLIENT_CERTIFICATE_ENV, "certificate-material")
    captured: dict[str, Any] = {}
    client = FakeConfidentialClient([{"access_token": "token", "expires_in": 3600}])

    def factory(**kwargs: Any) -> FakeConfidentialClient:
        captured.update(kwargs)
        return client

    provider = AzureAuthProvider(application_factory=factory)
    provider.get_access_token()

    assert captured["client_credential"] == {"private_key": "certificate-material"}


def test_successful_token_is_redacted_cached_and_renewed_after_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid token is reused before expiry, then renewed with the same service principal."""

    fake_secret = "fake-secret-that-must-never-be-printed"
    _set_valid_secret_credentials(monkeypatch, fake_secret)
    current = datetime(2025, 1, 1, tzinfo=timezone.utc)
    client = FakeConfidentialClient(
        [
            {"access_token": "first-access-token", "expires_in": 10},
            {"access_token": "renewed-access-token", "expires_in": 3600},
        ]
    )
    provider = _provider(client, clock=lambda: current)

    first = provider.get_access_token()
    assert provider.get_access_token() is first
    current += timedelta(seconds=11)
    renewed = provider.get_access_token()

    assert isinstance(first, AccessToken)
    assert renewed is not first
    assert renewed.reveal() == "renewed-access-token"
    assert len(client.scopes) == 2
    assert "management.azure.com/.default" in client.scopes[0][0]
    for printable in (str(first), repr(first), str(RedactedValue(fake_secret)), repr(RedactedValue(fake_secret))):
        assert fake_secret not in printable


def test_initial_aad_rejection_preserves_reason_without_secret_exposure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Initial AAD rejections are distinguishable and retain their safe reason."""

    fake_secret = "rejection-secret-value"
    _set_valid_secret_credentials(monkeypatch, fake_secret)
    client = FakeConfidentialClient(
        [{"error": "invalid_client", "error_description": f"bad credential {fake_secret}"}]
    )

    with pytest.raises(AuthRejectedError) as exc_info:
        _provider(client).get_access_token()

    assert "bad credential" in str(exc_info.value)
    assert fake_secret not in str(exc_info.value)
    assert fake_secret not in repr(exc_info.value)


def test_initial_aad_timeout_is_distinguishable_and_does_not_expose_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An initial AAD call that exceeds the deadline raises AuthTimeoutError."""

    fake_secret = "initial-timeout-secret"
    _set_valid_secret_credentials(monkeypatch, fake_secret)
    client = FakeConfidentialClient(
        [lambda: (time.sleep(0.05), {"access_token": "too-late", "expires_in": 60})[1]]
    )

    with pytest.raises(AuthTimeoutError) as exc_info:
        _provider(client, timeout_seconds=0.001).get_access_token()

    assert fake_secret not in str(exc_info.value)
    assert fake_secret not in repr(exc_info.value)


def test_rejected_mid_run_renewal_raises_auth_renewal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A token failure after expiry is a renewal failure rather than a new initial failure."""

    fake_secret = "renewal-rejection-secret"
    _set_valid_secret_credentials(monkeypatch, fake_secret)
    current = datetime(2025, 1, 1, tzinfo=timezone.utc)
    client = FakeConfidentialClient(
        [
            {"access_token": "short-lived", "expires_in": 1},
            {"error": "invalid_client", "error_description": f"renewal denied {fake_secret}"},
        ]
    )
    provider = _provider(client, clock=lambda: current)
    provider.get_access_token()
    current += timedelta(seconds=2)

    with pytest.raises(AuthRenewalError) as exc_info:
        provider.get_access_token()

    assert "renewal" in str(exc_info.value).lower()
    assert fake_secret not in str(exc_info.value)
    assert fake_secret not in repr(exc_info.value)


def test_timed_out_mid_run_renewal_raises_auth_renewal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A renewal that exceeds the deadline is surfaced as a distinguishable renewal failure."""

    fake_secret = "renewal-timeout-secret"
    _set_valid_secret_credentials(monkeypatch, fake_secret)
    current = datetime(2025, 1, 1, tzinfo=timezone.utc)
    client = FakeConfidentialClient(
        [
            {"access_token": "short-lived", "expires_in": 1},
            lambda: (time.sleep(0.05), {"access_token": "too-late", "expires_in": 60})[1],
        ]
    )
    provider = _provider(client, clock=lambda: current, timeout_seconds=0.001)
    provider.get_access_token()
    current += timedelta(seconds=2)

    with pytest.raises(AuthRenewalError) as exc_info:
        provider.get_access_token()

    assert fake_secret not in str(exc_info.value)
    assert fake_secret not in repr(exc_info.value)


def _fake_cli_runner(*, returncode: int = 0, stdout: str = "", stderr: str = "") -> Any:
    def runner(_args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(_args, returncode, stdout=stdout, stderr=stderr)

    return runner


def test_arm_use_cli_skips_service_principal_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """ARM_USE_CLI=true needs no app-registration credentials at all."""

    monkeypatch.setenv(ARM_USE_CLI_ENV, "true")
    for name in (AZURE_TENANT_ID_ENV, AZURE_CLIENT_ID_ENV, AZURE_CLIENT_SECRET_ENV, AZURE_CLIENT_CERTIFICATE_ENV):
        monkeypatch.delenv(name, raising=False)

    provider = AzureAuthProvider(
        az_cli_runner=_fake_cli_runner(stdout='{"accessToken": "cli-token", "expires_on": 9999999999}')
    )
    token = provider.get_access_token()

    assert token.reveal() == "cli-token"


def test_arm_use_cli_surfaces_az_cli_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-zero az CLI exit is reported without dumping full command output."""

    monkeypatch.setenv(ARM_USE_CLI_ENV, "true")
    provider = AzureAuthProvider(
        az_cli_runner=_fake_cli_runner(returncode=1, stderr="Please run 'az login' to setup account.")
    )

    with pytest.raises(AuthRejectedError, match="az login"):
        provider.get_access_token()


def test_arm_use_cli_missing_binary_is_a_configuration_error() -> None:
    """A missing az CLI on PATH is distinguishable from a rejected token."""

    def runner(_args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess:
        raise FileNotFoundError("az")

    provider = AzureAuthProvider(use_cli=True, az_cli_runner=runner)

    with pytest.raises(AuthConfigurationError):
        provider.get_access_token()
