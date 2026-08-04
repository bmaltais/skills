#!/usr/bin/env python3
"""Append one dated optimization-log entry to a skill's CHANGELOG.md.

Fully mechanical: figures out the date and the next Step number, renders the
fixed Markdown block, and appends it. All judgment — what the edits are,
whether something counts as a regression — happens before this script runs.

Usage:
    python3 append_changelog.py <skill-dir> < entry.json

entry.json:
{
  "skill_name": "some-skill",
  "edits_applied": ["[op: append] Added guard for X — reasoning: observed 3x tool failure"],
  "deferred": ["[P3] Consider adding Z — only 1 occurrence, low confidence"],
  "regressions": ["(none)"],
  "meta_notes": ["Strategy: prefer deletion this round"]
}
Any list may be omitted or empty; it renders as "- (none)".
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

STEP_RE = re.compile(r"^## Session .* — Step (\d+)", re.M)


def next_step(text):
    steps = [int(m) for m in STEP_RE.findall(text)]
    return max(steps) + 1 if steps else 1


def bullets(items):
    return "\n".join(f"- {i}" for i in items) if items else "- (none)"


def render(entry, step):
    return f"""## Session {date.today().isoformat()} — Step {step}

### Edits Applied
{bullets(entry.get("edits_applied", []))}

### Deferred Edits (waiting for more signal)
{bullets(entry.get("deferred", []))}

### Observed Regressions from Previous Edits
{bullets(entry.get("regressions", []))}

### Meta Notes
{bullets(entry.get("meta_notes", []))}"""


def main(argv):
    if not argv:
        print("usage: append_changelog.py <skill-dir> < entry.json", file=sys.stderr)
        return 2

    skill_dir = Path(argv[0])
    changelog = skill_dir / "CHANGELOG.md"
    entry = json.load(sys.stdin)

    if changelog.exists():
        text = changelog.read_text(encoding="utf-8")
    else:
        name = entry.get("skill_name", skill_dir.name)
        text = f"# {name} Optimization Log\n"

    step = next_step(text)
    text = text.rstrip("\n") + "\n\n" + render(entry, step) + "\n"
    changelog.write_text(text, encoding="utf-8")
    print(f"{changelog}: appended Step {step}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
