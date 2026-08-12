"""Deterministic VM SKU / informal-size -> Compute_Quota_Family resolver.

This module implements the lookup rules the ``map-sku`` subcommand (task 5)
sits on top of:

- An exact, case-insensitive, whitespace-insensitive VM SKU name match
  against the mapping table (Req 2.1).
- A ratio-based lookup (vCPU count exactly equal, memory amount exactly
  equal treating GB and GiB as equivalent units) when only an informal size
  is given (Req 2.2).
- SKU name takes precedence over an informal size when a candidate carries
  both (Req 2.3).
- Deterministic behavior: the same input always produces the same outcome,
  since the table is static and lookups involve no randomness or external
  state (Req 2.5).
- A distinguishable outcome for "no SKU match" (``unmatched``) versus
  "informal size matches more than one Compute_Quota_Family"
  (``ambiguous_candidates``) versus "informal size matches exactly one
  family" (resolved) versus "neither field supplied" (incomplete) (Req 2.4,
  2.7, 2.8).

The table itself (``table.json``, alongside this module) is loaded once at
import time via :mod:`pathlib` / :mod:`importlib.resources`-free direct file
access, which is fine here since the table always ships next to this source
file inside the installed package.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_TABLE_PATH = Path(__file__).with_name("table.json")

# Outcome discriminators returned in ResolutionResult.outcome.
OUTCOME_RESOLVED = "resolved"
OUTCOME_AMBIGUOUS = "ambiguous"
OUTCOME_UNMATCHED = "unmatched"
OUTCOME_INCOMPLETE = "incomplete"

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_sku_name(sku_name: str) -> str:
    """Fold case and discard whitespace for exact SKU comparison.

    Disregards letter case and leading, trailing, and repeated internal
    whitespace, per Req 2.1's "exact, case-insensitive, whitespace-insensitive"
    matching rule.
    """

    return _WHITESPACE_RE.sub("", sku_name).lower()


@dataclass(frozen=True)
class TableEntry:
    """One row of the static mapping table."""

    sku_name: str
    quota_family: str
    vcpu: float
    memory_gib: float


@dataclass(frozen=True)
class ResolutionResult:
    """The outcome of resolving one VM SKU name or informal size.

    ``outcome`` is one of the ``OUTCOME_*`` constants above.

    - ``resolved``: ``quota_family`` is set, ``ambiguous_candidates`` is
      empty, ``unmatched`` is False.
    - ``ambiguous``: ``quota_family`` is ``None``, ``ambiguous_candidates``
      lists every distinct matching Compute_Quota_Family (more than one),
      ``unmatched`` is False. Only possible for an informal-size lookup
      (Req 2.7).
    - ``unmatched``: ``quota_family`` is ``None``, ``ambiguous_candidates``
      is empty, ``unmatched`` is True. Covers both an unrecognized SKU name
      (Req 2.8) and an informal size matching zero families.
    - ``incomplete``: neither a SKU name nor an informal size was supplied
      (Req 2.4); ``quota_family`` is ``None``, ``ambiguous_candidates`` is
      empty, ``unmatched`` is False.

    ``matched_input`` records the exact input value that produced this
    determination (the SKU name string, or a rendering of the informal
    size), for the audit trail (Req 2.6).
    """

    outcome: str
    quota_family: str | None
    ambiguous_candidates: tuple[str, ...]
    unmatched: bool
    matched_input: str | None


def _load_entries(table_path: Path = _TABLE_PATH) -> list[TableEntry]:
    raw = json.loads(table_path.read_text(encoding="utf-8"))
    entries: list[TableEntry] = []
    for row in raw["entries"]:
        entries.append(
            TableEntry(
                sku_name=row["sku_name"],
                quota_family=row["quota_family"],
                vcpu=row["vcpu"],
                memory_gib=row["memory_gib"],
            )
        )
    return entries


class SkuResolver:
    """Resolves VM SKU names and informal sizes to a Compute_Quota_Family.

    Loads the static mapping table once (per instance) and answers lookups
    against an in-memory index, so repeated calls within a single ``map-sku``
    invocation (e.g. batch mode via ``--input``) do not re-read or re-parse
    ``table.json`` per candidate.
    """

    def __init__(self, table_path: Path = _TABLE_PATH) -> None:
        self._entries = _load_entries(table_path)
        self._by_normalized_name: dict[str, TableEntry] = {
            _normalize_sku_name(entry.sku_name): entry for entry in self._entries
        }

    def resolve_sku_name(self, sku_name: str) -> ResolutionResult:
        """Exact, case-insensitive, whitespace-insensitive SKU name lookup (Req 2.1)."""

        normalized = _normalize_sku_name(sku_name)
        entry = self._by_normalized_name.get(normalized)
        if entry is None:
            return ResolutionResult(
                outcome=OUTCOME_UNMATCHED,
                quota_family=None,
                ambiguous_candidates=(),
                unmatched=True,
                matched_input=sku_name,
            )
        return ResolutionResult(
            outcome=OUTCOME_RESOLVED,
            quota_family=entry.quota_family,
            ambiguous_candidates=(),
            unmatched=False,
            matched_input=sku_name,
        )

    def resolve_informal_size(self, vcpu: float, memory_amount: float, memory_unit: str = "gib") -> ResolutionResult:
        """Ratio-based lookup by exact vCPU count and memory amount (Req 2.2).

        ``memory_unit`` may be ``"gib"`` or ``"gb"``; both are treated as
        equivalent units for this comparison, per Req 2.2. (This resolver
        treats the numeric GB and GiB values as directly comparable, i.e.
        1 GB == 1 GiB for matching purposes, matching the table's own GiB
        values.)
        """

        memory_gib = memory_amount
        matched_families: list[str] = []
        seen: set[str] = set()
        for entry in self._entries:
            if entry.vcpu == vcpu and entry.memory_gib == memory_gib:
                if entry.quota_family not in seen:
                    seen.add(entry.quota_family)
                    matched_families.append(entry.quota_family)

        matched_input = f"{vcpu} vCPU / {memory_amount} {memory_unit.upper()}"

        if len(matched_families) == 0:
            return ResolutionResult(
                outcome=OUTCOME_UNMATCHED,
                quota_family=None,
                ambiguous_candidates=(),
                unmatched=True,
                matched_input=matched_input,
            )
        if len(matched_families) == 1:
            return ResolutionResult(
                outcome=OUTCOME_RESOLVED,
                quota_family=matched_families[0],
                ambiguous_candidates=(),
                unmatched=False,
                matched_input=matched_input,
            )
        return ResolutionResult(
            outcome=OUTCOME_AMBIGUOUS,
            quota_family=None,
            ambiguous_candidates=tuple(matched_families),
            unmatched=False,
            matched_input=matched_input,
        )

    def resolve(
        self,
        *,
        sku_name: str | None = None,
        vcpu: float | None = None,
        memory_amount: float | None = None,
        memory_unit: str = "gib",
    ) -> ResolutionResult:
        """Resolve a candidate's VM SKU name and/or informal size.

        - If ``sku_name`` is a non-empty string (after stripping whitespace),
          it is used and the informal size fields are disregarded (Req 2.3),
          regardless of whether they were also supplied.
        - Otherwise, if both ``vcpu`` and ``memory_amount`` are supplied, an
          informal-size lookup is performed (Req 2.2).
        - Otherwise (neither a usable SKU name nor a complete informal size),
          the request is incomplete (Req 2.4).
        """

        if sku_name is not None and sku_name.strip():
            return self.resolve_sku_name(sku_name)

        if vcpu is not None and memory_amount is not None:
            return self.resolve_informal_size(vcpu, memory_amount, memory_unit)

        return ResolutionResult(
            outcome=OUTCOME_INCOMPLETE,
            quota_family=None,
            ambiguous_candidates=(),
            unmatched=False,
            matched_input=None,
        )


def to_resolution_dict(candidate_id: str, result: ResolutionResult) -> dict[str, Any]:
    """Render a ResolutionResult into the ``map-sku`` output schema from design.md.

    Shape: ``{"candidate_id", "quota_family", "matched_input",
    "ambiguous_candidates", "unmatched"}``. Provided here so the future
    ``map-sku`` subcommand (task 5) and this resolver agree on the exact
    dict shape without duplicating the mapping logic.
    """

    return {
        "candidate_id": candidate_id,
        "quota_family": result.quota_family,
        "matched_input": result.matched_input,
        "ambiguous_candidates": list(result.ambiguous_candidates),
        "unmatched": result.unmatched,
    }
