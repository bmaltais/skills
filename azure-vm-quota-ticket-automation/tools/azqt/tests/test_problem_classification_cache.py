"""Tests for run-scoped Azure Support classification lookups.

**Validates: Requirements 4.3**
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from azqt.azure.problem_classification_cache import (
    COMPUTE_VM_CORES_DISPLAY_NAME,
    MANAGEMENT_ENDPOINT,
    QUOTA_SERVICE_DISPLAY_NAME,
    SUPPORT_API_VERSION,
    ProblemClassificationCache,
    SupportClassificationIds,
)


@dataclass
class FakeResponse:
    """A successful in-memory response matching the lookup client's needs."""

    payload: dict[str, Any]

    def raise_for_status(self) -> None:
        """Model an HTTP 200 response."""

    def json(self) -> dict[str, Any]:
        """Return the configured JSON body."""

        return self.payload


class MockHttpSession:
    """Mocked HTTP layer that records calls and returns list-API fixtures."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        self.calls.append(
            {
                "url": url,
                "params": dict(params),
                "headers": dict(headers),
                "timeout": timeout,
            }
        )
        if url.endswith("/services"):
            return FakeResponse(
                {
                    "value": [
                        {
                            "name": "unrelated-service-guid",
                            "id": "/providers/Microsoft.Support/services/unrelated-service-guid",
                            "properties": {"displayName": "Billing"},
                        },
                        {
                            "name": "quota-service-guid",
                            "id": "/providers/Microsoft.Support/services/quota-service-guid",
                            "properties": {"displayName": QUOTA_SERVICE_DISPLAY_NAME},
                        },
                    ]
                }
            )
        if url.endswith("/problemClassifications"):
            return FakeResponse(
                {
                    "value": [
                        {
                            "name": "unrelated-classification-guid",
                            "id": (
                                "/providers/Microsoft.Support/services/quota-service-guid"
                                "/problemClassifications/unrelated-classification-guid"
                            ),
                            "properties": {"displayName": "Compute - VM availability"},
                        },
                        {
                            "name": "compute-vm-cores-guid",
                            "id": (
                                "/providers/Microsoft.Support/services/quota-service-guid"
                                "/problemClassifications/compute-vm-cores-guid"
                            ),
                            "properties": {"displayName": COMPUTE_VM_CORES_DISPLAY_NAME},
                        },
                    ]
                }
            )
        raise AssertionError(f"Unexpected URL: {url}")


def test_lookup_is_reused_across_submit_ticket_groups_in_one_run() -> None:
    """Two groups in one submit-tickets run share exactly one pair of list calls."""

    http = MockHttpSession()
    cache = ProblemClassificationCache(session=http, timeout_seconds=12.5)

    # These calls model payload construction for two distinct submit-tickets
    # groups owned by the same run.  Task 13 will invoke this cache at that
    # integration point once submit-tickets is implemented.
    first_group_ids = cache.resolve("a" * 32, "test-access-token")
    second_group_ids = cache.resolve("a" * 32, "test-access-token")

    expected = SupportClassificationIds(
        service_id="/providers/Microsoft.Support/services/quota-service-guid",
        problem_classification_id=(
            "/providers/Microsoft.Support/services/quota-service-guid"
            "/problemClassifications/compute-vm-cores-guid"
        ),
    )
    assert first_group_ids == expected
    assert second_group_ids is first_group_ids
    assert len(http.calls) == 2
    assert [call["url"] for call in http.calls] == [
        f"{MANAGEMENT_ENDPOINT}/providers/Microsoft.Support/services",
        (
            f"{MANAGEMENT_ENDPOINT}/providers/Microsoft.Support/services/"
            "quota-service-guid/problemClassifications"
        ),
    ]
    assert all(call["params"] == {"api-version": SUPPORT_API_VERSION} for call in http.calls)
    assert all(call["headers"] == {"Authorization": "Bearer test-access-token"} for call in http.calls)
    assert all(call["timeout"] == 12.5 for call in http.calls)


def test_lookup_is_not_shared_between_runs() -> None:
    """Each run resolves current Azure metadata independently, as required."""

    http = MockHttpSession()
    cache = ProblemClassificationCache(session=http)

    cache.resolve("a" * 32, "test-access-token")
    cache.resolve("b" * 32, "test-access-token")

    assert len(http.calls) == 4
