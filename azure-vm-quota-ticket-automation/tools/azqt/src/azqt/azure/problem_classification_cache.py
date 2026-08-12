"""Run-scoped lookup of Azure Support service and problem-classification IDs.

Azure Support requires clients to obtain service and problem-classification IDs
from its list APIs rather than embedding their GUID values.  This module keeps
that resolution in memory for the lifetime of one ``submit-tickets`` run: a
caller creates one :class:`ProblemClassificationCache` for its command and
uses :meth:`resolve` for every quota-request group.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Mapping, Protocol
from urllib.parse import quote

import requests

MANAGEMENT_ENDPOINT = "https://management.azure.com"
SUPPORT_API_VERSION = "2024-04-01"
QUOTA_SERVICE_DISPLAY_NAME = "Service and subscription limits (quotas)"
COMPUTE_VM_CORES_DISPLAY_NAME = "Compute-VM (cores-vCPUs) subscription limit increases"


class _HttpResponse(Protocol):
    """Minimal ``requests.Response`` surface used by the lookup client."""

    def raise_for_status(self) -> None:
        """Raise an exception for a non-successful HTTP status."""

    def json(self) -> Any:
        """Decode the response JSON payload."""


class _HttpSession(Protocol):
    """Minimal ``requests.Session`` surface used by the lookup client."""

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout: float,
    ) -> _HttpResponse:
        """Issue an authenticated GET request."""


class AzureSupportLookupError(RuntimeError):
    """The Azure Support metadata needed to create a quota ticket was unavailable."""


@dataclass(frozen=True)
class _ResourceMatch:
    """One listed resource's short ``name`` (a bare GUID) and full ``id`` path.

    ``name`` is used to build a nested lookup URL (e.g. the problem
    classifications list is scoped under the service's bare GUID); ``id`` is
    the fully-qualified resource path (``/providers/Microsoft.Support/...``)
    that Azure's ticket-create payload actually requires for ``serviceId``
    and ``problemClassificationId``.
    """

    name: str
    id: str


@dataclass(frozen=True)
class SupportClassificationIds:
    """Resolved Azure Support IDs for a Compute VM Cores quota ticket."""

    service_id: str
    problem_classification_id: str


class ProblemClassificationCache:
    """Resolve and cache quota-ticket classification IDs by run identifier.

    Cache entries are kept only in this object's process-local memory.  The
    ``submit-tickets`` command will own one instance, so all its groups for a
    given run share one Services request and one ProblemClassifications
    request, while a fresh command/run receives a fresh lookup.
    """

    def __init__(
        self,
        *,
        session: _HttpSession | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        self._session = session or requests.Session()
        self._timeout_seconds = timeout_seconds
        self._by_run: dict[str, SupportClassificationIds] = {}
        self._lock = threading.Lock()

    def resolve(self, run_id: str, access_token: str) -> SupportClassificationIds:
        """Return the IDs for ``run_id``, looking them up once when first needed.

        ``access_token`` is used solely in the outbound Authorization header;
        it is never retained in cache state or included in an exception.
        """

        if not run_id:
            raise ValueError("run_id must be non-empty.")
        if not access_token:
            raise ValueError("access_token must be non-empty.")

        with self._lock:
            cached = self._by_run.get(run_id)
            if cached is not None:
                return cached

            headers = {"Authorization": f"Bearer {access_token}"}
            service = self._find_resource(
                resource_name="service",
                url=f"{MANAGEMENT_ENDPOINT}/providers/Microsoft.Support/services",
                display_name=QUOTA_SERVICE_DISPLAY_NAME,
                headers=headers,
            )
            classification = self._find_resource(
                resource_name="problem classification",
                url=(
                    f"{MANAGEMENT_ENDPOINT}/providers/Microsoft.Support/services/"
                    f"{quote(service.name, safe='')}/problemClassifications"
                ),
                display_name=COMPUTE_VM_CORES_DISPLAY_NAME,
                headers=headers,
            )
            resolved = SupportClassificationIds(
                service_id=service.id,
                problem_classification_id=classification.id,
            )
            self._by_run[run_id] = resolved
            return resolved

    def _find_resource(
        self,
        *,
        resource_name: str,
        url: str,
        display_name: str,
        headers: Mapping[str, str],
    ) -> "_ResourceMatch":
        """List Azure Support resources and return the one with ``display_name``."""

        try:
            response = self._session.get(
                url,
                params={"api-version": SUPPORT_API_VERSION},
                headers=headers,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError, TypeError) as exc:
            raise AzureSupportLookupError(
                f"Unable to list Azure Support {resource_name}s."
            ) from exc

        if not isinstance(payload, Mapping):
            raise AzureSupportLookupError(
                f"Azure Support {resource_name} list returned an invalid response."
            )
        resources = payload.get("value")
        if not isinstance(resources, list):
            raise AzureSupportLookupError(
                f"Azure Support {resource_name} list returned no resource collection."
            )

        matches = [
            (resource.get("name"), resource.get("id"))
            for resource in resources
            if isinstance(resource, Mapping)
            and isinstance(resource.get("name"), str)
            and isinstance(resource.get("id"), str)
            and isinstance(resource.get("properties"), Mapping)
            and resource["properties"].get("displayName") == display_name
        ]
        if len(matches) != 1:
            raise AzureSupportLookupError(
                f"Azure Support {resource_name} named {display_name!r} was not uniquely available."
            )
        name, resource_id = matches[0]
        return _ResourceMatch(name=name, id=resource_id)
