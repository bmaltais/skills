"""Shared ``map-sku`` command logic.

This module converts the three CLI input shapes into one normalized candidate
shape, then resolves every candidate through :class:`SkuResolver`.  Keeping
that work outside the argparse handler makes it impossible for the single and
batch modes to drift into separate mapping behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from azqt.skumapping.resolver import SkuResolver, to_resolution_dict


@dataclass(frozen=True)
class SkuCandidate:
    """A candidate normalized from either direct CLI flags or batch JSON."""

    candidate_id: str
    sku_name: str | None
    vcpu: float | None
    memory_gib: float | None

    def audit_input(self) -> dict[str, Any]:
        """Return the original logical mapping input for the audit trail."""

        return {
            "vm_sku_name": self.sku_name,
            "informal_size_description": (
                None
                if self.vcpu is None and self.memory_gib is None
                else {"vcpu": self.vcpu, "memory_gib": self.memory_gib}
            ),
        }


def _number(value: Any, field_name: str, candidate_id: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Candidate {candidate_id!r} has a non-numeric {field_name}.")
    return float(value)


def _optional_sku(value: Any, candidate_id: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Candidate {candidate_id!r} has a non-string vm_sku_name.")
    return value


def candidate_from_batch_entry(entry: Any) -> SkuCandidate:
    """Validate and normalize one documented ``candidates.json`` entry."""

    if not isinstance(entry, dict):
        raise ValueError("Each candidates.json item must be an object.")

    candidate_id = entry.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        raise ValueError("Each candidates.json item requires a non-empty candidate_id.")

    sku_name = _optional_sku(entry.get("vm_sku_name"), candidate_id)
    informal_size = entry.get("informal_size_description")
    if informal_size is None:
        return SkuCandidate(candidate_id, sku_name, None, None)
    if not isinstance(informal_size, dict):
        raise ValueError(
            f"Candidate {candidate_id!r} has a non-object informal_size_description."
        )

    if "vcpu" not in informal_size or "memory_gib" not in informal_size:
        raise ValueError(
            f"Candidate {candidate_id!r} informal_size_description requires vcpu and memory_gib."
        )
    return SkuCandidate(
        candidate_id=candidate_id,
        sku_name=sku_name,
        vcpu=_number(informal_size["vcpu"], "informal_size_description.vcpu", candidate_id),
        memory_gib=_number(
            informal_size["memory_gib"], "informal_size_description.memory_gib", candidate_id
        ),
    )


def load_batch_candidates(input_path: str | Path) -> list[SkuCandidate]:
    """Read and normalize the documented array form of ``candidates.json``."""

    path = Path(input_path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Unable to read candidates input {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Candidates input {path} is not valid JSON: {exc.msg}") from exc

    if not isinstance(raw, list):
        raise ValueError("Candidates input must be a JSON array.")
    return [candidate_from_batch_entry(entry) for entry in raw]


def resolve_candidates(candidates: list[SkuCandidate]) -> list[tuple[SkuCandidate, dict[str, Any]]]:
    """Resolve candidates through the task-4 resolver and render CLI results."""

    resolver = SkuResolver()
    return [
        (
            candidate,
            to_resolution_dict(
                candidate.candidate_id,
                resolver.resolve(
                    sku_name=candidate.sku_name,
                    vcpu=candidate.vcpu,
                    memory_amount=candidate.memory_gib,
                ),
            ),
        )
        for candidate in candidates
    ]
