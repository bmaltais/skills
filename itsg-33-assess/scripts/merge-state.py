#!/usr/bin/env python3
"""Merge itsg-33-assess family fragments into assessment-state.yaml.

Usage: merge-state.py <fragments-dir> <old-state-path> <new-state-path> <profile>

Reads every non-scratch JSON fragment in <fragments-dir> (files written by
write-fragment.py) and merges them into a single controls map. This script
is the sole writer of assessment-state.yaml: for any control a fragment
marks "cached": true, the finding/confidence/files_read already stored in
<old-state-path> are used verbatim, discarding whatever the fragment wrote
for those fields, so a no-op re-run cannot drift stored text regardless of
what an individual family subagent produced.

<old-state-path> may not exist (fresh run); it is then treated as having no
prior controls. <profile> drives the (fully mechanical) plausibility check.
<new-state-path> may be the same path as <old-state-path> for an in-place
update — the old file is fully read before the new one is written.
"""
import glob
import json
import os
import sys
from datetime import datetime, timezone

REQUIRED_STATE_FIELDS = ["finding", "confidence", "files_read"]


def fail(message):
    print(f"merge-state: {message}", file=sys.stderr)
    sys.exit(1)


def load_old_state(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        fail(f"existing state file {path} is not valid json: {e}")
        return {}
    return data.get("controls", {}) or {}


def load_fragments(fragments_dir):
    paths = sorted(
        p for p in glob.glob(os.path.join(fragments_dir, "*.json"))
        if not p.endswith(".input.json")
    )
    if not paths:
        fail(f"no fragment files found in {fragments_dir}")

    merged = {}
    for path in paths:
        try:
            with open(path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            fail(f"fragment {path} is not valid json: {e}")
            continue

        family = data.get("family", os.path.splitext(os.path.basename(path))[0])
        for control_id, control in data.get("controls", {}).items():
            if control_id in merged:
                fail(f"control {control_id} appears in more than one fragment "
                     f"(duplicate found in {path}, family {family})")
            merged[control_id] = control
    return merged


def resolve_control(control_id, control, old_controls):
    if control.get("cached"):
        old = old_controls.get(control_id)
        if old is None:
            fail(f"{control_id}: marked cached but has no prior entry in the existing state file")
            return None
        source, source_desc = old, "existing state file"
    else:
        source, source_desc = control, "fragment"

    missing = [field for field in REQUIRED_STATE_FIELDS if field not in source]
    if missing:
        fail(f"{control_id}: {source_desc} entry is missing required field(s): {missing}")
        return None
    return {field: source[field] for field in REQUIRED_STATE_FIELDS}


def apply_plausibility_check(controls, profile):
    if profile != "PBMM":
        return

    def all_not_assessable(prefix):
        matching = {cid: c for cid, c in controls.items() if cid.startswith(prefix + "-")}
        return bool(matching) and all(c["finding"] == "Not Assessable" for c in matching.values())

    if all_not_assessable("SC") and all_not_assessable("IA"):
        controls["PLAUSIBILITY-WARNING"] = {
            "finding": "Not Assessable",
            "confidence": (
                "PBMM declared but no encryption, auth, or network config was found. "
                "Verify the repo contains the relevant IaC or manifests, or that the "
                "system boundary is correctly scoped."
            ),
            "files_read": {},
        }


def main():
    if len(sys.argv) != 5:
        fail("usage: merge-state.py <fragments-dir> <old-state-path> <new-state-path> <profile>")
    fragments_dir, old_state_path, new_state_path, profile = sys.argv[1:5]

    old_controls = load_old_state(old_state_path)
    fragment_controls = load_fragments(fragments_dir)

    merged = {}
    for control_id, control in fragment_controls.items():
        merged[control_id] = resolve_control(control_id, control, old_controls)

    apply_plausibility_check(merged, profile)

    new_state = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "controls": merged,
    }
    with open(new_state_path, "w") as f:
        json.dump(new_state, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"merge-state: wrote {len(merged)} controls to {new_state_path}")


if __name__ == "__main__":
    main()
