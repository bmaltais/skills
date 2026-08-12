"""Service-principal and az-CLI-delegated authentication for Azure AD.

Credentials are read only from the local process environment.  They are never
accepted by CLI arguments, persisted in run state, or exposed through normal
string representations.  The provider caches a successful access token until
its Azure-provided expiry and renews it on demand.

When ``ARM_USE_CLI=true`` is set, no app registration is required at all: a
token is requested from the local az CLI's already-authenticated session
instead of via MSAL service-principal credentials.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Protocol, Sequence

import msal

AZURE_TENANT_ID_ENV = "AZURE_TENANT_ID"
AZURE_CLIENT_ID_ENV = "AZURE_CLIENT_ID"
AZURE_CLIENT_SECRET_ENV = "AZURE_CLIENT_SECRET"
AZURE_CLIENT_CERTIFICATE_ENV = "AZURE_CLIENT_CERTIFICATE"
AZURE_CLIENT_CERTIFICATE_THUMBPRINT_ENV = "AZURE_CLIENT_CERTIFICATE_THUMBPRINT"
ARM_USE_CLI_ENV = "ARM_USE_CLI"
MANAGEMENT_SCOPE: tuple[str, ...] = ("https://management.azure.com/.default",)
MANAGEMENT_RESOURCE = "https://management.azure.com/"
_REDACTED = "***REDACTED***"


def _is_truthy(value: str | None) -> bool:
    """Match Terraform's ARM_USE_CLI truthiness so both tools agree on the mode."""

    return value is not None and value.strip().lower() in ("1", "true", "yes")


class AuthError(RuntimeError):
    """Base error for an unsuccessful initial Azure AD token request."""


class AuthConfigurationError(AuthError):
    """Raised before contacting Azure AD when service-principal config is incomplete."""


class AuthTimeoutError(AuthError):
    """Raised when Azure AD does not complete a token request within the deadline."""


class AuthRejectedError(AuthError):
    """Raised when Azure AD returns a token response without a usable token."""


class AuthRenewalError(AuthError):
    """Raised when renewing an expired token fails after an earlier success."""


@dataclass(frozen=True)
class RedactedValue:
    """A secret value that can be used internally without being printable.

    Only :meth:`reveal` exposes the raw value, and that method is kept within
    this module's boundary when handing credentials to MSAL or a bearer token
    to the eventual Azure HTTP client.
    """

    _value: str = field(repr=False)

    def reveal(self) -> str:
        """Return the raw value for an in-process trusted Azure library call."""

        return self._value

    def __str__(self) -> str:
        return _REDACTED

    def __repr__(self) -> str:
        return f"{type(self).__name__}({_REDACTED!r})"


@dataclass(frozen=True)
class AccessToken:
    """A redacted Azure access token with its absolute UTC expiration time."""

    _token: RedactedValue = field(repr=False)
    expires_at: datetime

    def reveal(self) -> str:
        """Return the token only for constructing an in-process Authorization header."""

        return self._token.reveal()

    def is_valid(self, now: datetime) -> bool:
        """Return whether the token expires strictly after ``now``."""

        return self.expires_at > now

    def __str__(self) -> str:
        return _REDACTED

    def __repr__(self) -> str:
        return f"AccessToken(expires_at={self.expires_at.isoformat()!r}, token={_REDACTED!r})"


@dataclass(frozen=True)
class ServicePrincipalCredentials:
    """Validated service-principal settings loaded from the local environment."""

    tenant_id: str
    client_id: str
    client_secret: RedactedValue | None = field(default=None, repr=False)
    certificate: RedactedValue | None = field(default=None, repr=False)
    certificate_thumbprint: str | None = None

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> "ServicePrincipalCredentials":
        """Load and validate credentials without calling Azure AD.

        A populated certificate deliberately takes precedence over a populated
        client secret, matching the service-principal requirement.  Blank
        values are treated as absent so configuration failures name the actual
        missing component before MSAL is constructed or invoked.
        """

        source = os.environ if environ is None else environ
        tenant_id = _nonempty(source.get(AZURE_TENANT_ID_ENV))
        client_id = _nonempty(source.get(AZURE_CLIENT_ID_ENV))
        client_secret = _nonempty(source.get(AZURE_CLIENT_SECRET_ENV))
        certificate = _nonempty(source.get(AZURE_CLIENT_CERTIFICATE_ENV))
        thumbprint = _nonempty(source.get(AZURE_CLIENT_CERTIFICATE_THUMBPRINT_ENV))

        missing: list[str] = []
        if tenant_id is None:
            missing.append("tenant ID")
        if client_id is None:
            missing.append("client ID")
        if client_secret is None and certificate is None:
            missing.append("client secret or certificate")
        if missing:
            raise AuthConfigurationError(
                "Azure AD service-principal configuration is missing "
                + ", ".join(missing)
                + "."
            )

        return cls(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=RedactedValue(client_secret) if certificate is None else None,
            certificate=RedactedValue(certificate) if certificate is not None else None,
            certificate_thumbprint=thumbprint if certificate is not None else None,
        )

    def msal_client_credential(self) -> str | dict[str, str]:
        """Return the private credential shape required by MSAL.

        MSAL expects certificate client credentials as a mapping whose private
        key is the local certificate material.  A thumbprint is included when
        the operator configured one; MSAL accepts that optional field and it
        allows certificate-auth setups that require explicit thumbprints.
        """

        if self.certificate is not None:
            credential = {"private_key": self.certificate.reveal()}
            if self.certificate_thumbprint is not None:
                credential["thumbprint"] = self.certificate_thumbprint
            return credential
        assert self.client_secret is not None
        return self.client_secret.reveal()


class _ConfidentialClient(Protocol):
    def acquire_token_for_client(self, *, scopes: Sequence[str]) -> Mapping[str, Any]:
        """Acquire one app-only access token from Azure AD."""


def _nonempty(value: str | None) -> str | None:
    """Treat whitespace-only configuration values as absent without altering content."""

    if value is None or not value.strip():
        return None
    return value


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AzureAuthProvider:
    """Acquire, redact, cache, and renew a service-principal Azure AD token."""

    def __init__(
        self,
        credentials: ServicePrincipalCredentials | None = None,
        *,
        environ: Mapping[str, str] | None = None,
        application_factory: Callable[..., _ConfidentialClient] = msal.ConfidentialClientApplication,
        timeout_seconds: float = 30.0,
        clock: Callable[[], datetime] = _utc_now,
        use_cli: bool | None = None,
        az_cli_runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    ) -> None:
        """Create a provider after validating environment-backed credentials.

        ``application_factory`` and ``clock`` are injection seams for tests;
        production callers use MSAL and the current UTC time.  No token request
        is made during construction.

        When ``ARM_USE_CLI=true`` is set (as ``163ent-devops.user`` does for a
        delegated user login), service-principal credentials are not required
        at all; tokens are instead requested from the already-logged-in az
        CLI via ``az account get-access-token``.
        """

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        source = os.environ if environ is None else environ
        self._use_cli = _is_truthy(source.get(ARM_USE_CLI_ENV)) if use_cli is None else use_cli
        self._az_cli_runner = az_cli_runner
        self._timeout_seconds = timeout_seconds
        self._clock = clock
        self._token: AccessToken | None = None
        if self._use_cli:
            self.credentials = None
            self._application = None
        else:
            self.credentials = credentials or ServicePrincipalCredentials.from_environment(environ)
            self._application = application_factory(
                client_id=self.credentials.client_id,
                client_credential=self.credentials.msal_client_credential(),
                authority=f"https://login.microsoftonline.com/{self.credentials.tenant_id}",
            )

    def get_access_token(self) -> AccessToken:
        """Return a valid cached token, acquiring or renewing it when required.

        If a previously acquired token has expired, any acquisition failure is
        surfaced as :class:`AuthRenewalError`; first-request failures retain
        their more specific initial-authentication error type.
        """

        now = self._clock()
        if self._token is not None and self._token.is_valid(now):
            return self._token

        renewing = self._token is not None
        try:
            token = self._acquire_token()
        except AuthError as exc:
            if renewing:
                raise AuthRenewalError(
                    f"Azure AD access-token renewal failed: {_safe_reason(str(exc))}"
                ) from exc
            raise

        self._token = token
        return token

    def _acquire_token(self) -> AccessToken:
        """Execute the configured credential flow within the mandatory deadline."""

        if self._use_cli:
            return self._acquire_token_via_cli()

        result = self._call_with_timeout()
        if not isinstance(result, Mapping):
            raise AuthRejectedError("Azure AD returned an invalid token response.")

        raw_token = result.get("access_token")
        if not isinstance(raw_token, str) or not raw_token.strip():
            reason = result.get("error_description") or result.get("error")
            if reason:
                raise AuthRejectedError(
                    "Azure AD rejected service-principal credentials: "
                    + _safe_reason(str(reason))
                )
            raise AuthRejectedError("Azure AD did not return an access token.")

        expires_at = self._expiry_from_response(result)
        if expires_at <= self._clock():
            raise AuthRejectedError("Azure AD returned an already-expired access token.")
        return AccessToken(RedactedValue(raw_token), expires_at)

    def _call_with_timeout(self) -> Mapping[str, Any]:
        """Invoke MSAL on a daemon worker so a blocked request cannot delay a run."""

        completed: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

        def request_token() -> None:
            try:
                completed.put((True, self._application.acquire_token_for_client(scopes=MANAGEMENT_SCOPE)))
            except BaseException as exc:  # pragma: no cover - exercised through public errors
                completed.put((False, exc))

        worker = threading.Thread(target=request_token, daemon=True)
        worker.start()
        try:
            succeeded, value = completed.get(timeout=self._timeout_seconds)
        except queue.Empty as exc:
            raise AuthTimeoutError(
                f"Azure AD token request timed out after {self._timeout_seconds:g} seconds."
            ) from exc

        if succeeded:
            return value
        if isinstance(value, TimeoutError):
            raise AuthTimeoutError("Azure AD token request timed out.") from value
        raise AuthError("Azure AD token request failed.") from value

    def _expiry_from_response(self, result: Mapping[str, Any]) -> datetime:
        """Resolve Azure's ``expires_on`` or ``expires_in`` into a UTC instant."""

        expires_on = result.get("expires_on")
        if expires_on is not None:
            try:
                return datetime.fromtimestamp(float(expires_on), tz=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                pass

        expires_in = result.get("expires_in", 3600)
        try:
            seconds = float(expires_in)
        except (TypeError, ValueError) as exc:
            raise AuthRejectedError("Azure AD returned an invalid token expiration.") from exc
        if seconds <= 0:
            raise AuthRejectedError("Azure AD returned an already-expired access token.")
        return self._clock() + timedelta(seconds=seconds)

    def _acquire_token_via_cli(self) -> AccessToken:
        """Request a management-scope token from the already-logged-in az CLI.

        This is the delegated-user path ``163ent-devops.user`` sets up via
        ``ARM_USE_CLI=true``: no app registration exists, so the token is
        whatever identity ``az login`` is currently holding.
        """

        try:
            completed = self._az_cli_runner(
                ["az", "account", "get-access-token", "--resource", MANAGEMENT_RESOURCE, "--output", "json"],
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise AuthConfigurationError("az CLI is not installed or not on PATH.") from exc
        except subprocess.TimeoutExpired as exc:
            raise AuthTimeoutError(
                f"az CLI token request timed out after {self._timeout_seconds:g} seconds."
            ) from exc

        if completed.returncode != 0:
            raise AuthRejectedError(
                "az CLI could not provide an access token: " + (completed.stderr or "").strip()
            )

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AuthRejectedError("az CLI returned an invalid token response.") from exc

        raw_token = payload.get("accessToken")
        if not isinstance(raw_token, str) or not raw_token.strip():
            raise AuthRejectedError("az CLI did not return an access token.")

        return AccessToken(RedactedValue(raw_token), self._expiry_from_cli_payload(payload))

    def _expiry_from_cli_payload(self, payload: Mapping[str, Any]) -> datetime:
        """Resolve az CLI's ``expires_on``/``expiresOn`` into a UTC instant."""

        expires_on = payload.get("expires_on")
        if expires_on is not None:
            try:
                return datetime.fromtimestamp(float(expires_on), tz=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                pass

        expires_on_str = payload.get("expiresOn")
        if isinstance(expires_on_str, str):
            try:
                # ponytail: az CLI's expiresOn is local time with no offset; treating it
                # as UTC only makes renewal early, never late. Add real tz handling if
                # that early-renewal margin ever proves too aggressive.
                return datetime.strptime(expires_on_str, "%Y-%m-%d %H:%M:%S.%f").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                pass

        raise AuthRejectedError("az CLI returned an access token without a usable expiration.")


def _safe_reason(reason: str) -> str:
    """Prevent configured credential values from appearing in an error string."""

    sanitized = reason
    for value in (
        os.environ.get(AZURE_CLIENT_SECRET_ENV),
        os.environ.get(AZURE_CLIENT_CERTIFICATE_ENV),
    ):
        if value:
            sanitized = sanitized.replace(value, _REDACTED)
    return sanitized
