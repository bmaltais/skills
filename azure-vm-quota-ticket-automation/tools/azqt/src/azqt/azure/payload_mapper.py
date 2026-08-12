"""Group confirmed quota requests and construct Azure Support ticket payloads.

This module is deliberately independent of HTTP and authentication.  It turns
already-confirmed request records into deterministic, ticket-scoped payload
results so a later submission layer can submit every valid ticket while
reporting any invalid ticket without losing the remaining work.

Azure Support tickets (``Microsoft.Support/supportTickets``) are scoped to a
single subscription, so one ticket per subscription is the coarsest grouping
Azure allows -- requests for different subscriptions can never share a
ticket.  Within a subscription, Azure's quota-ticket payload format allows
several region/quota-family combinations in the *same* ticket via multiple
``quotaChangeRequests`` entries, so requests are further split into per
region/quota-family "line items" that become those entries rather than
separate tickets.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from azqt.azure.problem_classification_cache import SupportClassificationIds

COMPUTE_VM_CORES_TITLE = "Compute VM Cores quota increase"
_SEVERITY_URGENCY: dict[str, int] = {"minimal": 1, "moderate": 2, "critical": 3}


@dataclass(frozen=True)
class ConfirmedQuotaRequest:
    """The confirmed-request fields needed for grouping and ticket mapping."""

    candidate_id: str
    subscription_id: str
    region: str
    quota_family: str
    requested_quota: int
    justification: str | None
    contact_name: str
    contact_email: str
    contact_phone: str | None
    country: str
    preferred_time_zone: str
    preferred_support_language: str
    severity_level: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ConfirmedQuotaRequest":
        """Create a request from the documented ``confirmed_requests.json`` shape.

        Validation intentionally happens during payload mapping so an error can
        identify both the offending request and its enclosing group.
        """

        candidate_id = value.get("candidate_id")
        return cls(
            candidate_id=candidate_id if isinstance(candidate_id, str) else "<unknown>",
            subscription_id=value.get("subscription_id"),
            region=value.get("region"),
            quota_family=value.get("quota_family"),
            requested_quota=value.get("requested_quota"),
            justification=value.get("justification"),
            contact_name=value.get("contact_name"),
            contact_email=value.get("contact_email"),
            contact_phone=value.get("contact_phone"),
            country=value.get("country"),
            preferred_time_zone=value.get("preferred_time_zone"),
            preferred_support_language=value.get("preferred_support_language"),
            severity_level=value.get("severity_level"),
        )


@dataclass(frozen=True)
class QuotaRequestGroup:
    """Requests sharing Azure's subscription, region, and quota-family scope.

    This is one ticket *line item*: Azure's quota payload lets several of
    these share a single ticket for the same subscription (see
    :class:`SubscriptionTicketGroup`), each becoming one ``quotaChangeRequests``
    entry.
    """

    subscription_id: str
    region: str
    quota_family: str
    requests: tuple[ConfirmedQuotaRequest, ...]

    @property
    def requested_quota_total(self) -> int:
        """Return the requested quota sum after payload-field validation."""

        return sum(request.requested_quota for request in self.requests)

    @property
    def key(self) -> tuple[str, str, str]:
        """Return the user-visible key, preserving the first request's region text."""

        return (self.subscription_id, self.region, self.quota_family)

    def describe(self) -> str:
        """Render a stable, useful identifier for mapping errors and audit events."""

        return (
            "(subscription_id={!r}, region={!r}, quota_family={!r})".format(
                self.subscription_id, self.region, self.quota_family
            )
        )


@dataclass(frozen=True)
class SubscriptionTicketGroup:
    """Every confirmed request destined for one Azure Support ticket.

    Azure Support tickets are scoped to a single subscription, so this is
    the unit that maps to exactly one ticket. It holds one or more
    :class:`QuotaRequestGroup` line items -- each a distinct region/quota-family
    combination within the subscription -- which become that ticket's
    ``quotaChangeRequests`` entries (Req 4.1-4.4).
    """

    subscription_id: str
    line_items: tuple[QuotaRequestGroup, ...]

    @property
    def requests(self) -> tuple[ConfirmedQuotaRequest, ...]:
        """Every confirmed request in this ticket, across all line items."""

        return tuple(
            request for line_item in self.line_items for request in line_item.requests
        )

    def describe(self) -> str:
        """Render a stable, useful identifier for mapping errors and audit events."""

        line_items_text = ", ".join(
            "(region={!r}, quota_family={!r})".format(item.region, item.quota_family)
            for item in self.line_items
        )
        return "(subscription_id={!r}, line_items=[{}])".format(
            self.subscription_id, line_items_text
        )


class MappingError(ValueError):
    """A field could not be represented in one Azure Support ticket payload."""

    def __init__(
        self,
        group: QuotaRequestGroup | SubscriptionTicketGroup,
        request: ConfirmedQuotaRequest | None,
        field: str,
        reason: str,
    ) -> None:
        self.group = group
        self.request = request
        self.field = field
        self.reason = reason
        request_label = "group" if request is None else f"request {request.candidate_id!r}"
        super().__init__(
            f"Unable to map quota request group {group.describe()}: "
            f"{request_label} field {field!r} {reason}"
        )


@dataclass(frozen=True)
class PayloadMappingResult:
    """The independent payload or mapping error for one ticket's requests."""

    group: SubscriptionTicketGroup
    payload: dict[str, Any] | None
    error: MappingError | None

    @property
    def succeeded(self) -> bool:
        """Whether this group's payload was built successfully."""

        return self.payload is not None and self.error is None


def _as_request(value: ConfirmedQuotaRequest | Mapping[str, Any]) -> ConfirmedQuotaRequest:
    if isinstance(value, ConfirmedQuotaRequest):
        return value
    if isinstance(value, Mapping):
        return ConfirmedQuotaRequest.from_mapping(value)
    raise TypeError("Each confirmed quota request must be an object or ConfirmedQuotaRequest.")


def _grouping_text(request: ConfirmedQuotaRequest, field: str) -> str:
    value = getattr(request, field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"request {request.candidate_id!r} field {field!r} must be a non-empty string")
    return value


def group_confirmed_requests(
    requests: Sequence[ConfirmedQuotaRequest | Mapping[str, Any]],
) -> list[SubscriptionTicketGroup]:
    """Group requests into one ticket per subscription (Req 4.1).

    Requests are grouped by exact subscription_id first, since that is the
    only grouping Azure Support tickets themselves allow. Within a
    subscription, requests are further split into line items by exact
    quota_family and case-insensitive region -- each line item becomes one
    ``quotaChangeRequests`` entry in that subscription's single ticket.

    Subscription order, line-item order, and the region spelling from each
    line item's first member are retained. This preserves Extraction_Agent
    order for phone fallback while comparing regions according to
    Requirement 4.1.
    """

    line_items_by_subscription: dict[str, dict[tuple[str, str], list[ConfirmedQuotaRequest]]] = {}
    line_item_fields: dict[str, dict[tuple[str, str], tuple[str, str]]] = {}
    subscription_order: list[str] = []

    for raw_request in requests:
        request = _as_request(raw_request)
        try:
            subscription_id = _grouping_text(request, "subscription_id")
            region = _grouping_text(request, "region")
            quota_family = _grouping_text(request, "quota_family")
        except ValueError as exc:
            # There is no valid Azure group key without one of these fields, so
            # identify the request/field directly rather than silently grouping it.
            raise ValueError(f"Cannot group confirmed quota request: {exc}") from exc

        if subscription_id not in line_items_by_subscription:
            subscription_order.append(subscription_id)
            line_items_by_subscription[subscription_id] = {}
            line_item_fields[subscription_id] = {}

        line_item_key = (region.casefold(), quota_family)
        subscription_line_items = line_items_by_subscription[subscription_id]
        subscription_line_item_fields = line_item_fields[subscription_id]
        if line_item_key not in subscription_line_items:
            subscription_line_items[line_item_key] = []
            subscription_line_item_fields[line_item_key] = (region, quota_family)
        subscription_line_items[line_item_key].append(request)

    groups: list[SubscriptionTicketGroup] = []
    for subscription_id in subscription_order:
        subscription_line_items = line_items_by_subscription[subscription_id]
        subscription_line_item_fields = line_item_fields[subscription_id]
        line_items = tuple(
            QuotaRequestGroup(
                subscription_id,
                *subscription_line_item_fields[line_item_key],
                tuple(members),
            )
            for line_item_key, members in subscription_line_items.items()
        )
        groups.append(SubscriptionTicketGroup(subscription_id, line_items))

    return groups


def _required_text(
    group: QuotaRequestGroup,
    request: ConfirmedQuotaRequest,
    field: str,
) -> str:
    value = getattr(request, field)
    if not isinstance(value, str) or not value.strip():
        raise MappingError(group, request, field, "must be a non-empty string.")
    return value.strip()


def _requested_quota(group: QuotaRequestGroup, request: ConfirmedQuotaRequest) -> int:
    value = request.requested_quota
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MappingError(group, request, "requested_quota", "must be a positive integer.")
    return value


def _vm_family_series_name(group: QuotaRequestGroup, quota_family: str) -> str:
    """Render a resolver quota_family (e.g. ``standardDav6Family``) as the
    human-readable ``VMFamily`` series name Azure's quota payload requires
    (e.g. ``"Dav6 Series"``), per https://aka.ms/supportrpquotarequestpayload.
    """

    prefix, suffix = "standard", "Family"
    if not quota_family.startswith(prefix) or not quota_family.endswith(suffix):
        raise MappingError(
            group,
            None,
            "quota_family",
            f"{quota_family!r} does not match the expected 'standard<Series>Family' shape.",
        )
    return quota_family[len(prefix):-len(suffix)] + " Series"


def _description(group: SubscriptionTicketGroup) -> str:
    attributed_justifications: list[str] = []
    for request in group.requests:
        value = request.justification
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        if not isinstance(value, str):
            raise MappingError(group, request, "justification", "must be a string when provided.")
        attributed_justifications.append(
            f"Confirmed quota request {request.candidate_id}: {value.strip()}"
        )

    if not attributed_justifications:
        raise MappingError(
            group,
            None,
            "justification",
            "has no non-empty justification in any group member.",
        )

    # Mirrors the structured quotaTicketDetails payload as plain text, since
    # that field isn't rendered in the Azure Portal's ticket view.
    requested_quota_lines = [
        f"- {line_item.region} / {_vm_family_series_name(line_item, line_item.quota_family)}: "
        f"{line_item.requested_quota_total}"
        for line_item in group.line_items
    ]

    return (
        "\n".join(attributed_justifications)
        + "\n\nRequested quota:\n"
        + "\n".join(requested_quota_lines)
    )


def _split_contact_name(group: SubscriptionTicketGroup, request: ConfirmedQuotaRequest, name: str) -> tuple[str, str]:
    """Split a full contact name into Azure's required firstName/lastName.

    Azure's ContactProfile has no single "full name" field, so the first
    whitespace-separated token becomes firstName and everything after it
    becomes lastName (Req: ContactProfile.lastName is non-optional).
    """

    parts = name.split(None, 1)
    if len(parts) != 2 or not parts[1].strip():
        raise MappingError(
            group,
            request,
            "contact_name",
            "must contain both a first and last name (Azure requires a non-empty lastName).",
        )
    return parts[0], parts[1].strip()


def _contact_details(group: SubscriptionTicketGroup) -> dict[str, str]:
    first_request = group.requests[0]
    canonical_name = _required_text(group, first_request, "contact_name")
    canonical_email = _required_text(group, first_request, "contact_email")
    canonical_country = _required_text(group, first_request, "country")
    canonical_time_zone = _required_text(group, first_request, "preferred_time_zone")
    canonical_language = _required_text(group, first_request, "preferred_support_language")

    conflicting_names = [canonical_name]
    conflicting_emails = [canonical_email]
    conflicting_countries = [canonical_country]
    conflicting_time_zones = [canonical_time_zone]
    conflicting_languages = [canonical_language]
    for request in group.requests[1:]:
        name = _required_text(group, request, "contact_name")
        email = _required_text(group, request, "contact_email")
        country = _required_text(group, request, "country")
        time_zone = _required_text(group, request, "preferred_time_zone")
        language = _required_text(group, request, "preferred_support_language")
        if name != canonical_name:
            conflicting_names.append(name)
        if email.casefold() != canonical_email.casefold():
            conflicting_emails.append(email)
        if country.casefold() != canonical_country.casefold():
            conflicting_countries.append(country)
        if time_zone != canonical_time_zone:
            conflicting_time_zones.append(time_zone)
        if language.casefold() != canonical_language.casefold():
            conflicting_languages.append(language)

    if len(conflicting_names) > 1:
        raise MappingError(
            group,
            None,
            "contact_name",
            f"has conflicting values: {conflicting_names!r}.",
        )
    if len(conflicting_emails) > 1:
        raise MappingError(
            group,
            None,
            "contact_email",
            f"has conflicting values: {conflicting_emails!r}.",
        )
    if len(conflicting_countries) > 1:
        raise MappingError(
            group,
            None,
            "country",
            f"has conflicting values: {conflicting_countries!r}.",
        )
    if len(conflicting_time_zones) > 1:
        raise MappingError(
            group,
            None,
            "preferred_time_zone",
            f"has conflicting values: {conflicting_time_zones!r}.",
        )
    if len(conflicting_languages) > 1:
        raise MappingError(
            group,
            None,
            "preferred_support_language",
            f"has conflicting values: {conflicting_languages!r}.",
        )

    first_name, last_name = _split_contact_name(group, first_request, canonical_name)
    contact_details = {
        "firstName": first_name,
        "lastName": last_name,
        "primaryEmailAddress": canonical_email,
        "preferredContactMethod": "email",
        "country": canonical_country,
        "preferredTimeZone": canonical_time_zone,
        "preferredSupportLanguage": canonical_language,
    }
    for request in group.requests:
        phone = request.contact_phone
        if phone is None or (isinstance(phone, str) and not phone.strip()):
            continue
        if not isinstance(phone, str):
            raise MappingError(group, request, "contact_phone", "must be a string when provided.")
        contact_details["phoneNumber"] = phone.strip()
        break
    return contact_details


def _severity(group: SubscriptionTicketGroup) -> str:
    resolved: list[tuple[ConfirmedQuotaRequest, str]] = []
    for request in group.requests:
        severity = request.severity_level
        if not isinstance(severity, str) or severity not in _SEVERITY_URGENCY:
            raise MappingError(
                group,
                request,
                "severity_level",
                "must be one of 'minimal', 'moderate', or 'critical'.",
            )
        resolved.append((request, severity))
    return max(resolved, key=lambda item: _SEVERITY_URGENCY[item[1]])[1]


class PayloadMapper:
    """Deterministically group confirmed requests and build their ticket payloads."""

    def group(
        self, requests: Sequence[ConfirmedQuotaRequest | Mapping[str, Any]]
    ) -> list[SubscriptionTicketGroup]:
        """Return one group per Azure Support ticket per Requirement 4.1."""

        return group_confirmed_requests(requests)

    def build_payload(
        self,
        group: SubscriptionTicketGroup,
        classification_ids: SupportClassificationIds,
    ) -> dict[str, Any]:
        """Construct one Compute VM Cores support-ticket request body for ``group``.

        Every line item in ``group`` shares one ticket -- and thus one
        description, contact, and severity -- but contributes its own
        ``quotaChangeRequests`` entry, since Azure scopes each entry to a
        single region and quota family (Req 4.2-4.4).
        """

        if not group.line_items:
            raise MappingError(group, None, "requests", "must contain at least one request.")
        if not isinstance(classification_ids.service_id, str) or not classification_ids.service_id:
            raise MappingError(group, None, "service_id", "is unavailable.")
        if (
            not isinstance(classification_ids.problem_classification_id, str)
            or not classification_ids.problem_classification_id
        ):
            raise MappingError(group, None, "problem_classification_id", "is unavailable.")

        quota_change_requests: list[dict[str, str]] = []
        for line_item in group.line_items:
            # Validate the line item's key and every quota before summing to
            # prevent a malformed member from being represented as a
            # plausible but wrong limit.
            for request in line_item.requests:
                _required_text(line_item, request, "subscription_id")
                _required_text(line_item, request, "region")
                _required_text(line_item, request, "quota_family")
            total_requested_quota = sum(
                _requested_quota(line_item, request) for request in line_item.requests
            )
            vm_family = _vm_family_series_name(line_item, line_item.quota_family)
            quota_payload = json.dumps(
                {"VMFamily": vm_family, "NewLimit": total_requested_quota},
                separators=(",", ":"),
            )
            quota_change_requests.append({"region": line_item.region, "payload": quota_payload})

        return {
            "properties": {
                "title": COMPUTE_VM_CORES_TITLE,
                "description": _description(group),
                "advancedDiagnosticConsent": "No",
                "serviceId": classification_ids.service_id,
                "problemClassificationId": classification_ids.problem_classification_id,
                "severity": _severity(group),
                "contactDetails": _contact_details(group),
                "quotaTicketDetails": {
                    "quotaChangeRequestVersion": "1.0",
                    "quotaChangeRequests": quota_change_requests,
                },
            }
        }

    def map_groups(
        self,
        groups: Sequence[SubscriptionTicketGroup],
        classification_ids: SupportClassificationIds,
    ) -> list[PayloadMappingResult]:
        """Build all group payloads, retaining an error only on its own group."""

        results: list[PayloadMappingResult] = []
        for group in groups:
            try:
                payload = self.build_payload(group, classification_ids)
            except MappingError as error:
                results.append(PayloadMappingResult(group=group, payload=None, error=error))
            else:
                results.append(PayloadMappingResult(group=group, payload=payload, error=None))
        return results

    def map_requests(
        self,
        requests: Sequence[ConfirmedQuotaRequest | Mapping[str, Any]],
        classification_ids: SupportClassificationIds,
    ) -> list[PayloadMappingResult]:
        """Group then map requests, preserving independent group outcomes."""

        return self.map_groups(self.group(requests), classification_ids)


def build_payload(
    group: SubscriptionTicketGroup,
    classification_ids: SupportClassificationIds,
) -> dict[str, Any]:
    """Convenience wrapper for a caller mapping one already-formed group."""

    return PayloadMapper().build_payload(group, classification_ids)
