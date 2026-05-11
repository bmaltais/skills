#!/usr/bin/env python3
"""
recall.py — surfaces prior upgrade patterns for a given resource type.

Usage:
    uv run python tools/recall.py <resource-type>
    uv run python tools/recall.py container_group
    uv run python tools/recall.py kubernetes_cluster
"""

import json
import sys
from pathlib import Path

PATTERNS_FILE = Path(__file__).parent.parent / "memory" / "patterns.jsonl"


def load_patterns() -> list[dict]:
    if not PATTERNS_FILE.exists():
        return []
    patterns = []
    with PATTERNS_FILE.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    patterns.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return patterns


def main():
    resource_type = sys.argv[1].lower().strip() if len(sys.argv) > 1 else ""

    patterns = load_patterns()

    if not patterns:
        print("No prior upgrade lessons recorded.")
        print(f"Run tools/lesson.py {resource_type or '<resource>'} after your first upgrade.")
        return

    # Exact match first, then partial
    exact = [p for p in patterns if p.get("resource_type", "").lower() == resource_type]
    partial = [p for p in patterns if resource_type and resource_type in p.get("resource_type", "").lower() and p not in exact]
    other = [p for p in patterns if p not in exact and p not in partial]

    print(f"=== eslz-module-upgrade recall: '{resource_type}' ===\n")

    if exact:
        print(f"--- Exact matches ({len(exact)}) ---")
        for p in exact:
            _print_pattern(p)

    if partial:
        print(f"--- Partial matches ({len(partial)}) ---")
        for p in partial:
            _print_pattern(p)

    if not exact and not partial:
        print("No matches for this resource type.\n")

    if other:
        print(f"--- Other recorded upgrades ({len(other)}) ---")
        for p in other:
            print(f"  {p.get('resource_type', '?')} ({p.get('date', '?')}): {p.get('notes', '')[:80]}")
        print()

    print("Tip: common patterns documented in references/compat-patterns.md and references/hcl-patterns.md")


def _print_pattern(p: dict):
    print(f"Resource : {p.get('resource_type', '?')}")
    print(f"Date     : {p.get('date', '?')}")
    print(f"Tests    : {p.get('test_count', '?')}")
    print(f"Moved    : {p.get('moved_blocks', '?')}")
    if p.get("bugs_fixed"):
        print(f"Bugs fixed:")
        for bug in p["bugs_fixed"]:
            print(f"  - {bug}")
    if p.get("features_added"):
        print(f"Features added:")
        for feat in p["features_added"]:
            print(f"  - {feat}")
    if p.get("notes"):
        print(f"Notes    : {p['notes']}")
    print()


if __name__ == "__main__":
    main()
