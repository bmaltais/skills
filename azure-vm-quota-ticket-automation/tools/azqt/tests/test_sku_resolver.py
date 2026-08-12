"""Unit tests for azqt.skumapping.resolver.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.7, 2.8**
"""

from __future__ import annotations

from azqt.skumapping.resolver import (
    OUTCOME_AMBIGUOUS,
    OUTCOME_INCOMPLETE,
    OUTCOME_RESOLVED,
    OUTCOME_UNMATCHED,
    SkuResolver,
)


def test_exact_sku_match() -> None:
    """A recognized SKU name resolves to its table quota family (Req 2.1)."""

    resolver = SkuResolver()

    result = resolver.resolve(sku_name="Standard_D2s_v5")

    assert result.outcome == OUTCOME_RESOLVED
    assert result.quota_family == "standardDSv5Family"
    assert result.unmatched is False
    assert result.ambiguous_candidates == ()
    assert result.matched_input == "Standard_D2s_v5"


def test_exact_sku_match_amd_v6_general_purpose() -> None:
    """A recognized AMD Dasv6 SKU name resolves to standardDav6Family (Req 2.1)."""

    resolver = SkuResolver()

    result = resolver.resolve(sku_name="Standard_D2as_v6")

    assert result.outcome == OUTCOME_RESOLVED
    assert result.quota_family == "standardDav6Family"
    assert result.unmatched is False


def test_exact_sku_match_intel_v6_general_purpose() -> None:
    """A recognized Intel Dsv6 SKU name resolves to standardDSv6Family (Req 2.1)."""

    resolver = SkuResolver()

    result = resolver.resolve(sku_name="Standard_D2s_v6")

    assert result.outcome == OUTCOME_RESOLVED
    assert result.quota_family == "standardDSv6Family"
    assert result.unmatched is False


def test_exact_sku_match_amd_v6_general_purpose_local_disk() -> None:
    """A recognized AMD Dadsv6 (local temp disk) SKU name resolves to standardDADSv6Family (Req 2.1)."""

    resolver = SkuResolver()

    result = resolver.resolve(sku_name="Standard_D2ads_v6")

    assert result.outcome == OUTCOME_RESOLVED
    assert result.quota_family == "standardDADSv6Family"
    assert result.unmatched is False


def test_exact_sku_match_amd_v6_memory_optimized() -> None:
    """A recognized AMD Easv6 SKU name resolves to standardEav6Family (Req 2.1)."""

    resolver = SkuResolver()

    result = resolver.resolve(sku_name="Standard_E8as_v6")

    assert result.outcome == OUTCOME_RESOLVED
    assert result.quota_family == "standardEav6Family"
    assert result.unmatched is False


def test_exact_sku_match_intel_v6_memory_optimized() -> None:
    """A recognized Intel Esv6 SKU name resolves to standardESv6Family (Req 2.1)."""

    resolver = SkuResolver()

    result = resolver.resolve(sku_name="Standard_E8s_v6")

    assert result.outcome == OUTCOME_RESOLVED
    assert result.quota_family == "standardESv6Family"
    assert result.unmatched is False


def test_exact_sku_match_amd_v6_memory_optimized_local_disk() -> None:
    """A recognized AMD Eadsv6 (local temp disk) SKU name resolves to standardEADSv6Family (Req 2.1)."""

    resolver = SkuResolver()

    result = resolver.resolve(sku_name="Standard_E8ads_v6")

    assert result.outcome == OUTCOME_RESOLVED
    assert result.quota_family == "standardEADSv6Family"
    assert result.unmatched is False


def test_sku_match_is_case_and_whitespace_insensitive() -> None:
    """Case differences and any whitespace do not affect the match (Req 2.1)."""

    resolver = SkuResolver()

    canonical = resolver.resolve(sku_name="Standard_D2s_v5")
    varied_case = resolver.resolve(sku_name="  standard_  d2S_ v5   ")
    repeated_leading_trailing_whitespace = resolver.resolve(
        sku_name="\t\t  Standard_D2s_v5   \t  "
    )

    assert varied_case.outcome == OUTCOME_RESOLVED
    assert varied_case.quota_family == canonical.quota_family
    assert repeated_leading_trailing_whitespace.outcome == OUTCOME_RESOLVED
    assert repeated_leading_trailing_whitespace.quota_family == canonical.quota_family


def test_informal_size_matches_single_family() -> None:
    """An informal size unique to one family resolves unambiguously (Req 2.2)."""

    resolver = SkuResolver()

    result = resolver.resolve(vcpu=1, memory_amount=3.5, memory_unit="gib")

    assert result.outcome == OUTCOME_RESOLVED
    assert result.quota_family == "standardDFamily"
    assert result.ambiguous_candidates == ()
    assert result.unmatched is False


def test_informal_size_treats_gb_and_gib_as_equivalent() -> None:
    """Memory expressed as GB vs GiB does not change the match outcome (Req 2.2)."""

    resolver = SkuResolver()

    as_gib = resolver.resolve(vcpu=1, memory_amount=3.5, memory_unit="gib")
    as_gb = resolver.resolve(vcpu=1, memory_amount=3.5, memory_unit="gb")

    assert as_gib.outcome == as_gb.outcome == OUTCOME_RESOLVED
    assert as_gib.quota_family == as_gb.quota_family == "standardDFamily"


def test_informal_size_2vcpu_8gib_is_ambiguous_across_families() -> None:
    """The repeated 2vCPU/8GiB sample size spans all Dsv generations plus Dasv6 (Req 2.7)."""

    resolver = SkuResolver()

    result = resolver.resolve(vcpu=2, memory_amount=8, memory_unit="gib")

    assert result.outcome == OUTCOME_AMBIGUOUS
    assert result.quota_family is None
    assert result.unmatched is False
    assert set(result.ambiguous_candidates) == {
        "standardDSv3Family",
        "standardDSv4Family",
        "standardDSv5Family",
        "standardDav6Family",
        "standardDSv6Family",
        "standardDADSv6Family",
    }


def test_informal_size_8vcpu_64gib_is_ambiguous_across_families() -> None:
    """The repeated 8vCPU/64GiB sample size spans Esv3, Esv5 and Easv6 (Req 2.7)."""

    resolver = SkuResolver()

    result = resolver.resolve(vcpu=8, memory_amount=64, memory_unit="gib")

    assert result.outcome == OUTCOME_AMBIGUOUS
    assert result.quota_family is None
    assert result.unmatched is False
    assert set(result.ambiguous_candidates) == {
        "standardESv3Family",
        "standardESv5Family",
        "standardEav6Family",
        "standardESv6Family",
        "standardEADSv6Family",
    }


def test_unmatched_sku_name() -> None:
    """A SKU name absent from the table is reported as unmatched, not ambiguous (Req 2.8)."""

    resolver = SkuResolver()

    result = resolver.resolve(sku_name="Standard_ZZ99_not_a_real_sku")

    assert result.outcome == OUTCOME_UNMATCHED
    assert result.unmatched is True
    assert result.quota_family is None
    assert result.ambiguous_candidates == ()


def test_informal_size_matching_zero_families_is_unmatched() -> None:
    """An informal size with no table entry behaves like unmatched, distinct from ambiguous."""

    resolver = SkuResolver()

    result = resolver.resolve(vcpu=99, memory_amount=999, memory_unit="gib")

    assert result.outcome == OUTCOME_UNMATCHED
    assert result.unmatched is True
    assert result.quota_family is None
    assert result.ambiguous_candidates == ()


def test_missing_both_sku_and_informal_size_is_incomplete() -> None:
    """Neither a SKU name nor an informal size supplied signals incompleteness (Req 2.4)."""

    resolver = SkuResolver()

    result = resolver.resolve()

    assert result.outcome == OUTCOME_INCOMPLETE
    assert result.quota_family is None
    assert result.unmatched is False
    assert result.ambiguous_candidates == ()
    assert result.matched_input is None


def test_sku_name_takes_precedence_over_informal_size_when_both_present() -> None:
    """When both fields are present, the SKU name wins and the size is disregarded (Req 2.3)."""

    resolver = SkuResolver()

    result = resolver.resolve(
        sku_name="Standard_D2s_v5", vcpu=2, memory_amount=8, memory_unit="gib"
    )

    assert result.outcome == OUTCOME_RESOLVED
    assert result.quota_family == "standardDSv5Family"
    assert result.matched_input == "Standard_D2s_v5"


def test_resolution_is_deterministic_across_repeated_calls() -> None:
    """The same input always produces the same outcome (Req 2.5)."""

    resolver = SkuResolver()

    first = resolver.resolve(sku_name="Standard_D2s_v5")
    second = resolver.resolve(sku_name="Standard_D2s_v5")
    assert first == second

    first_size = resolver.resolve(vcpu=2, memory_amount=8, memory_unit="gib")
    second_size = resolver.resolve(vcpu=2, memory_amount=8, memory_unit="gib")
    assert first_size == second_size
