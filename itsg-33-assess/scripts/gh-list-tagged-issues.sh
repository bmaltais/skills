#!/usr/bin/env bash
# gh-list-tagged-issues.sh — List open GitHub issues carrying a given label.
#
# Usage: gh-list-tagged-issues.sh <label>
#
# Wraps: gh issue list --label <label> --state open --json number,title,body,labels
# Prints the raw JSON array to stdout on success.

set -euo pipefail

LABEL="${1:?Usage: gh-list-tagged-issues.sh <label>}"

echo "==> Listing open issues labelled '${LABEL}'..." >&2

if ! OUTPUT=$(gh issue list --label "$LABEL" --state open --json number,title,body,labels 2>&1); then
  echo "gh-list-tagged-issues: gh issue list failed: ${OUTPUT}" >&2
  exit 1
fi

echo "$OUTPUT"
