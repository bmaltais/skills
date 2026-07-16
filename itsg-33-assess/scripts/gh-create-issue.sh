#!/usr/bin/env bash
# gh-create-issue.sh — Create a GitHub issue with one or more labels.
#
# Usage: gh-create-issue.sh <title> <labels> <body-file>
#   <labels> is a comma-separated list, e.g. "itsg-33:gap,P1"
#
# Wraps: gh issue create --title <title> --label <l1> [--label <l2> ...] --body-file <body-file>
# Prints "<number> <url>" to stdout on success.

set -euo pipefail

TITLE="${1:?Usage: gh-create-issue.sh <title> <labels> <body-file>}"
LABELS="${2:?Usage: gh-create-issue.sh <title> <labels> <body-file>}"
BODY_FILE="${3:?Usage: gh-create-issue.sh <title> <labels> <body-file>}"

if [[ ! -f "$BODY_FILE" ]]; then
  echo "gh-create-issue: body file not found: ${BODY_FILE}" >&2
  exit 1
fi

LABEL_ARGS=()
IFS=',' read -ra LABEL_LIST <<< "$LABELS"
for label in "${LABEL_LIST[@]}"; do
  LABEL_ARGS+=(--label "$label")
done

echo "==> Creating issue '${TITLE}'..." >&2

STDERR_FILE=$(mktemp)
trap 'rm -f "$STDERR_FILE"' EXIT
if ! URL=$(gh issue create --title "$TITLE" "${LABEL_ARGS[@]}" --body-file "$BODY_FILE" 2>"$STDERR_FILE"); then
  echo "gh-create-issue: gh issue create failed: $(cat "$STDERR_FILE")" >&2
  exit 1
fi

NUMBER="${URL##*/}"
echo "${NUMBER} ${URL}"
