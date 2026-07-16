#!/usr/bin/env bash
# gh-create-pr.sh — Open a draft GitHub PR, optionally closing a gap issue.
#
# Usage: gh-create-pr.sh <title> <body-file> [<closes-issue-number>]
#
# Wraps: gh pr create --draft --title <title> --body-file <file>
# When <closes-issue-number> is given, appends "Closes #<N>" to the body
# before creating the PR. Prints the PR URL to stdout on success.

set -euo pipefail

TITLE="${1:?Usage: gh-create-pr.sh <title> <body-file> [<closes-issue-number>]}"
BODY_FILE="${2:?Usage: gh-create-pr.sh <title> <body-file> [<closes-issue-number>]}"
CLOSES_NUMBER="${3:-}"

if [[ ! -f "$BODY_FILE" ]]; then
  echo "gh-create-pr: body file not found: ${BODY_FILE}" >&2
  exit 1
fi

FINAL_BODY_FILE="$BODY_FILE"
STDERR_FILE=$(mktemp)
trap 'rm -f "$STDERR_FILE"' EXIT
if [[ -n "$CLOSES_NUMBER" ]]; then
  FINAL_BODY_FILE=$(mktemp)
  trap 'rm -f "$FINAL_BODY_FILE" "$STDERR_FILE"' EXIT
  cat "$BODY_FILE" > "$FINAL_BODY_FILE"
  printf '\nCloses #%s\n' "$CLOSES_NUMBER" >> "$FINAL_BODY_FILE"
fi

echo "==> Creating draft PR '${TITLE}'..." >&2

if ! URL=$(gh pr create --draft --title "$TITLE" --body-file "$FINAL_BODY_FILE" 2>"$STDERR_FILE"); then
  echo "gh-create-pr: gh pr create failed: $(cat "$STDERR_FILE")" >&2
  exit 1
fi

echo "$URL"
