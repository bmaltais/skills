#!/usr/bin/env python3
"""Validate and canonically write an itsg-33-assess fragment file.

Usage: write-fragment.py <family> <input-json-path> <output-json-path>

Reads a family subagent's per-control assessment data as JSON, validates
it against the fragment schema, and writes a canonical JSON fragment.
Exits non-zero with a specific message on any validation failure so the
calling subagent can fix its input and retry, per SKILL.md Step 4's
"malformed output" failure handling.
"""
import json
import re
import sys

VALID_FINDINGS = {"Pass", "Fail", "Not Assessable"}
REQUIRED_CONTROL_FIELDS = [
    "finding",
    "confidence",
    "risk_summary",
    "implementation_approach",
    "evidence_artefacts",
    "client_responsibility",
    "files_read",
]
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def fail(message):
    print(f"write-fragment: {message}", file=sys.stderr)
    sys.exit(1)


def validate(family, data):
    if not isinstance(data, dict):
        fail("top-level JSON must be an object")
    if data.get("family") != family:
        fail(f"family mismatch: expected '{family}', got {data.get('family')!r}")
    controls = data.get("controls")
    if not isinstance(controls, dict) or not controls:
        fail("'controls' must be a non-empty object")

    for control_id, control in controls.items():
        if not isinstance(control, dict):
            fail(f"{control_id}: control entry must be an object")
        for field in REQUIRED_CONTROL_FIELDS:
            if field not in control:
                fail(f"{control_id}: missing required field '{field}'")

        if control["finding"] not in VALID_FINDINGS:
            fail(f"{control_id}: invalid finding {control['finding']!r}, "
                 f"must be one of {sorted(VALID_FINDINGS)}")

        if not isinstance(control["confidence"], str) or not control["confidence"].strip():
            fail(f"{control_id}: 'confidence' must be a non-empty string")

        if not isinstance(control["evidence_artefacts"], list):
            fail(f"{control_id}: 'evidence_artefacts' must be a list")

        files_read = control["files_read"]
        if not isinstance(files_read, dict):
            fail(f"{control_id}: 'files_read' must be an object")
        for path, digest in files_read.items():
            if not isinstance(digest, str) or not SHA256_RE.match(digest):
                fail(f"{control_id}: files_read[{path!r}] is not a 64-char lowercase "
                     f"SHA-256 hex digest: {digest!r}")

        if "cached" in control and not isinstance(control["cached"], bool):
            fail(f"{control_id}: 'cached' must be a boolean if present")


def main():
    if len(sys.argv) != 4:
        fail("usage: write-fragment.py <family> <input-json-path> <output-json-path>")
    family, input_path, output_path = sys.argv[1:4]

    try:
        with open(input_path) as f:
            raw = f.read()
    except OSError as e:
        fail(f"cannot read input file: {e}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        fail(f"input is not valid json: {e}")

    validate(family, data)

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"write-fragment: wrote {len(data['controls'])} controls to {output_path}")


if __name__ == "__main__":
    main()
