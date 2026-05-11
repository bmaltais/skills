#!/usr/bin/env python3
"""
lesson.py — appends an upgrade lesson entry to memory/patterns.jsonl.

Usage:
    uv run python tools/lesson.py <resource-type> \
        --moved-blocks <yes|no> \
        --test-count <N> \
        --bugs-fixed "bug1" "bug2" \
        --features-added "feat1" "feat2" \
        --notes "<non-obvious decisions or provider quirks>"

Example:
    uv run python tools/lesson.py container_group \
        --moved-blocks no \
        --test-count 8 \
        --bugs-fixed "regex escape [^\\/]" "environment_variables missing try()" \
        --features-added "init_container" "diagnostics" "multi-port" \
        --notes "try(tolist(x),[x]) required for single-or-list normalization; can() causes type error"
"""

import argparse
import json
from datetime import date
from pathlib import Path

PATTERNS_FILE = Path(__file__).parent.parent / "memory" / "patterns.jsonl"


def main():
    parser = argparse.ArgumentParser(description="Record an ESLZ module upgrade lesson")
    parser.add_argument("resource_type", help="AzureRM resource type (e.g. container_group)")
    parser.add_argument("--moved-blocks", choices=["yes", "no"], default="no")
    parser.add_argument("--test-count", type=int, default=0)
    parser.add_argument("--bugs-fixed", nargs="*", default=[])
    parser.add_argument("--features-added", nargs="*", default=[])
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    entry = {
        "resource_type": args.resource_type.lower().strip(),
        "date": str(date.today()),
        "moved_blocks": args.moved_blocks,
        "test_count": args.test_count,
        "bugs_fixed": args.bugs_fixed,
        "features_added": args.features_added,
        "notes": args.notes,
    }

    PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with PATTERNS_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"Lesson recorded: {entry['resource_type']} ({entry['date']})")
    print(f"  moved_blocks   : {entry['moved_blocks']}")
    print(f"  test_count     : {entry['test_count']}")
    if entry["bugs_fixed"]:
        print(f"  bugs_fixed     : {', '.join(entry['bugs_fixed'])}")
    if entry["features_added"]:
        print(f"  features_added : {', '.join(entry['features_added'])}")
    if entry["notes"]:
        print(f"  notes          : {entry['notes']}")
    print(f"\nStored in: {PATTERNS_FILE}")


if __name__ == "__main__":
    main()
