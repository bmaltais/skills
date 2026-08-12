"""Unit tests for confirmed-request grouping and Azure ticket payload mapping.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11**
"""

from __future__ import annotations

import json

import pytest

from azqt.azure.payload_mapper import (
    COMPUTE_VM_CORES_TITLE,
    ConfirmedQuotaRequest,
    MappingError,
    PayloadMapper,
    build_payload,
    group_confirmed_requests,
)
from azqt.azure.problem_classification_cache import SupportClassificationIds


CLASSIFICATION_IDS = SupportClassificationIds(
    service_id="quota-service-guid",
    problem_classification_id="compute-vm-cores-guid",
)


def request(candidate_id: str, **overrides: object) -> ConfirmedQuotaRequest:
    """Return one valid confirmed request with concise override support."""

    values: dict[str, object] = {
        "candidate_id": candidate_id,
        "subscription_id": "subscription-a",
        "region": "EastUS",
        "quota_family": "standardDSv5Family",
        "requested_quota": 8,
        "justification": f"Scale-out requested by {candidate_id}",
        "contact_name": "Ada Lovelace",
        "contact_email": "ada@example.test",
        "contact_phone": None,
        "country": "USA",
        "preferred_time_zone": "Pacific Standard Time",
        "preferred_support_language": "en-us",
        "severity_level": "moderate",
    }
    values.update(overrides)
    return ConfirmedQuotaRequest(**values)  # type: ignore[arg-type]


def test_grouping_forms_one_ticket_per_subscription_with_region_family_line_items() -> None:
    """One ticket group per subscription; region/family become its line items (Req 4.1)."""

    groups = group_confirmed_requests(
        [
            request("c1"),
            request("c2", region="eastus"),
            request("c3", subscription_id="Subscription-A"),
            request("c4", region="WestUS"),
            request("c5", quota_family="standardESv5Family"),
        ]
    )

    assert len(groups) == 2
    subscription_a, subscription_a_other_case = groups
    assert subscription_a.subscription_id == "subscription-a"
    assert [line_item.key for line_item in subscription_a.line_items] == [
        ("subscription-a", "EastUS", "standardDSv5Family"),
        ("subscription-a", "WestUS", "standardDSv5Family"),
        ("subscription-a", "EastUS", "standardESv5Family"),
    ]
    assert [item.candidate_id for item in subscription_a.line_items[0].requests] == ["c1", "c2"]
    assert [item.candidate_id for item in subscription_a.line_items[1].requests] == ["c4"]
    assert [item.candidate_id for item in subscription_a.line_items[2].requests] == ["c5"]
    assert [request.candidate_id for request in subscription_a.requests] == [
        "c1",
        "c2",
        "c4",
        "c5",
    ]

    assert subscription_a_other_case.subscription_id == "Subscription-A"
    assert [item.candidate_id for item in subscription_a_other_case.requests] == ["c3"]


def test_grouping_combines_multiple_regions_and_families_into_one_ticket() -> None:
    """A subscription with several regions/families still yields exactly one ticket group."""

    groups = group_confirmed_requests(
        [
            request("d1", subscription_id="shared-sub", region="EastUS", quota_family="standardDASv6Family"),
            request("d2", subscription_id="shared-sub", region="WestUS", quota_family="standardEASv6Family"),
        ]
    )

    assert len(groups) == 1
    assert groups[0].subscription_id == "shared-sub"
    assert len(groups[0].line_items) == 2


def test_payload_builds_one_quota_change_request_per_line_item() -> None:
    """A ticket spanning several regions/families gets one payload with several entries (Req 4.2-4.4)."""

    group = group_confirmed_requests(
        [
            request(
                "d1",
                subscription_id="shared-sub",
                region="EastUS",
                quota_family="standardDASv6Family",
                requested_quota=4,
            ),
            request(
                "d2",
                subscription_id="shared-sub",
                region="EastUS",
                quota_family="standardDASv6Family",
                requested_quota=6,
            ),
            request(
                "d3",
                subscription_id="shared-sub",
                region="WestUS",
                quota_family="standardEASv6Family",
                requested_quota=8,
            ),
        ]
    )[0]

    quota_change_requests = build_payload(group, CLASSIFICATION_IDS)["properties"][
        "quotaTicketDetails"
    ]["quotaChangeRequests"]

    assert len(quota_change_requests) == 2
    assert quota_change_requests[0]["region"] == "EastUS"
    assert json.loads(quota_change_requests[0]["payload"]) == {
        "VMFamily": "DASv6 Series",
        "NewLimit": 10,
    }
    assert quota_change_requests[1]["region"] == "WestUS"
    assert json.loads(quota_change_requests[1]["payload"]) == {
        "VMFamily": "EASv6 Series",
        "NewLimit": 8,
    }


def test_payload_sums_quota_and_constructs_compute_vm_cores_shape() -> None:
    """A group maps to one Azure payload with a summed NewLimit (Req 4.2-4.4)."""

    group = group_confirmed_requests(
        [request("c1", requested_quota=8), request("c2", requested_quota=12)]
    )[0]

    payload = build_payload(group, CLASSIFICATION_IDS)
    properties = payload["properties"]
    quota_change = properties["quotaTicketDetails"]["quotaChangeRequests"][0]

    assert properties["title"] == COMPUTE_VM_CORES_TITLE
    assert properties["serviceId"] == "quota-service-guid"
    assert properties["problemClassificationId"] == "compute-vm-cores-guid"
    assert properties["advancedDiagnosticConsent"] == "No"
    assert quota_change["region"] == "EastUS"
    assert json.loads(quota_change["payload"]) == {
        "VMFamily": "DSv5 Series",
        "NewLimit": 20,
    }


def test_payload_description_attributes_each_non_empty_justification() -> None:
    """Descriptions include source IDs and omit empty justifications (Req 4.5)."""

    group = group_confirmed_requests(
        [
            request("c1", justification="Production workload expansion"),
            request("c2", justification="  "),
            request("c3", justification="QA verification capacity"),
        ]
    )[0]

    description = build_payload(group, CLASSIFICATION_IDS)["properties"]["description"]

    assert description == (
        "Confirmed quota request c1: Production workload expansion\n"
        "Confirmed quota request c3: QA verification capacity\n"
        "\n"
        "Requested quota:\n"
        "- EastUS / DSv5 Series: 24"
    )
    assert "c2" not in description


def test_group_without_a_justification_is_excluded_with_its_group_identifier() -> None:
    """A group with no usable justification produces a mapping error (Req 4.5)."""

    group = group_confirmed_requests([request("c1", justification=None)])[0]

    with pytest.raises(MappingError, match="subscription-a") as exc_info:
        build_payload(group, CLASSIFICATION_IDS)

    assert exc_info.value.field == "justification"


def test_contact_unanimity_trims_comparison_and_uses_name_case_sensitively() -> None:
    """Equivalent trimmed contacts map once; casing in names remains significant (Req 4.6)."""

    matching_group = group_confirmed_requests(
        [
            request("c1", contact_name=" Ada Lovelace ", contact_email="ADA@EXAMPLE.TEST"),
            request("c2", contact_name="Ada Lovelace", contact_email="ada@example.test"),
        ]
    )[0]

    contact = build_payload(matching_group, CLASSIFICATION_IDS)["properties"]["contactDetails"]
    assert contact["firstName"] == "Ada"
    assert contact["lastName"] == "Lovelace"
    assert contact["primaryEmailAddress"] == "ADA@EXAMPLE.TEST"

    mismatched_group = group_confirmed_requests(
        [request("c1", contact_name="Ada Lovelace"), request("c2", contact_name="ada Lovelace")]
    )[0]
    with pytest.raises(MappingError, match="contact_name") as exc_info:
        build_payload(mismatched_group, CLASSIFICATION_IDS)
    assert "Ada Lovelace" in str(exc_info.value)
    assert "ada Lovelace" in str(exc_info.value)


def test_contact_email_conflict_names_the_group_and_conflicting_values() -> None:
    """Different normalized emails exclude the group rather than choosing one (Req 4.7)."""

    group = group_confirmed_requests(
        [
            request("c1", contact_email="ada@example.test"),
            request("c2", contact_email="grace@example.test"),
        ]
    )[0]

    with pytest.raises(MappingError, match="contact_email") as exc_info:
        build_payload(group, CLASSIFICATION_IDS)

    error_text = str(exc_info.value)
    assert group.describe() in error_text
    assert "ada@example.test" in error_text
    assert "grace@example.test" in error_text


def test_phone_uses_first_non_empty_value_in_extraction_order_or_is_omitted() -> None:
    """Phone fallback preserves member order and omits the field when unavailable (Req 4.8)."""

    with_phone = group_confirmed_requests(
        [
            request("c1", contact_phone=" "),
            request("c2", contact_phone=" 555-0102 "),
            request("c3", contact_phone="555-0103"),
        ]
    )[0]
    no_phone = group_confirmed_requests(
        [request("c4", contact_phone=None), request("c5", contact_phone="")]
    )[0]

    assert (
        build_payload(with_phone, CLASSIFICATION_IDS)["properties"]["contactDetails"]["phoneNumber"]
        == "555-0102"
    )
    assert "phoneNumber" not in build_payload(no_phone, CLASSIFICATION_IDS)["properties"][
        "contactDetails"
    ]


def test_severity_uses_the_most_urgent_value_in_a_mixed_group() -> None:
    """Critical outranks moderate and minimal; a unanimous value is retained (Req 4.9-4.10)."""

    mixed_group = group_confirmed_requests(
        [
            request("c1", severity_level="minimal"),
            request("c2", severity_level="moderate"),
            request("c3", severity_level="critical"),
        ]
    )[0]
    unanimous_group = group_confirmed_requests(
        [request("c4", severity_level="minimal"), request("c5", severity_level="minimal")]
    )[0]

    assert build_payload(mixed_group, CLASSIFICATION_IDS)["properties"]["severity"] == "critical"
    assert build_payload(unanimous_group, CLASSIFICATION_IDS)["properties"]["severity"] == "minimal"


def test_unmappable_field_excludes_only_its_group_and_does_not_stop_other_groups() -> None:
    """An invalid field yields a group-scoped MappingError while valid groups survive (Req 4.11)."""

    results = PayloadMapper().map_requests(
        [
            request("bad", severity_level="urgent"),
            request(
                "good",
                subscription_id="subscription-b",
                quota_family="standardESv5Family",
                severity_level="minimal",
            ),
        ],
        CLASSIFICATION_IDS,
    )

    failed, succeeded = results
    assert failed.group.subscription_id == "subscription-a"
    assert failed.payload is None
    assert isinstance(failed.error, MappingError)
    assert failed.error.request is not None
    assert failed.error.request.candidate_id == "bad"
    assert failed.error.field == "severity_level"
    assert succeeded.group.subscription_id == "subscription-b"
    assert succeeded.error is None
    assert succeeded.payload is not None
    assert succeeded.payload["properties"]["severity"] == "minimal"
