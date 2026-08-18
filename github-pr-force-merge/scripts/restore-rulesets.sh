#!/usr/bin/env bash
# Emergency restore: re-enable rulesets that were disabled by force-merge-pr.sh
# but never restored (e.g. terminal killed mid-run).
#
# Usage: restore-rulesets.sh <owner/repo> <PR_number>

set -euo pipefail

REPO_SLUG="${1:?Usage: restore-rulesets.sh <owner/repo> <PR_number>}"
PR_NUM="${2:?Usage: restore-rulesets.sh <owner/repo> <PR_number>}"
OWNER="${REPO_SLUG%%/*}"
REPO="${REPO_SLUG##*/}"

STATE_FILE="/tmp/gh-force-merge-${OWNER}-${REPO}-${PR_NUM}-rulesets.txt"

if [[ ! -s "$STATE_FILE" ]]; then
  echo "No state file found at $STATE_FILE — nothing to restore."
  exit 0
fi

while read -r rid; do
  [[ -z "$rid" ]] && continue
  gh api -X PUT "repos/$OWNER/$REPO/rulesets/$rid" -f enforcement=active >/dev/null \
    && echo "ruleset $rid -> active" \
    || echo "WARNING: failed to restore ruleset $rid"
done < "$STATE_FILE"

rm -f "$STATE_FILE"
