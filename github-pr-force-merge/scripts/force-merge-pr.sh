#!/usr/bin/env bash
# Force-merge a GitHub PR by temporarily disabling any repository rulesets
# that block the merge (e.g. required code-owner review) which admin
# bypass alone cannot skip, then restoring them afterward.
#
# Usage: force-merge-pr.sh <PR_URL_or_number> [owner/repo] [merge_method]
#   merge_method: merge | squash (default) | rebase
#
# Requires: gh CLI authenticated with an account that has admin on the repo.

set -euo pipefail

ARG1="${1:?Usage: force-merge-pr.sh <PR_URL_or_number> [owner/repo] [merge_method]}"
MERGE_METHOD="${3:-squash}"

# --- Resolve owner/repo/PR number -------------------------------------------
if [[ "$ARG1" =~ ^https://github.com/([^/]+)/([^/]+)/pull/([0-9]+) ]]; then
  OWNER="${BASH_REMATCH[1]}"
  REPO="${BASH_REMATCH[2]}"
  PR_NUM="${BASH_REMATCH[3]}"
elif [[ -n "${2:-}" ]]; then
  OWNER="${2%%/*}"
  REPO="${2##*/}"
  PR_NUM="$ARG1"
else
  # Fall back to the repo in the current working directory
  OWNER=$(gh repo view --json owner --jq '.owner.login')
  REPO=$(gh repo view --json name --jq '.name')
  PR_NUM="$ARG1"
fi

echo "Repo: $OWNER/$REPO   PR: #$PR_NUM   Merge method: $MERGE_METHOD"

STATE_FILE="/tmp/gh-force-merge-${OWNER}-${REPO}-${PR_NUM}-rulesets.txt"
: > "$STATE_FILE"

# --- Restore any disabled rulesets on exit (success, failure, or interrupt) -
restore_rulesets() {
  if [[ -s "$STATE_FILE" ]]; then
    echo "Restoring ruleset enforcement..."
    while read -r rid; do
      [[ -z "$rid" ]] && continue
      gh api -X PUT "repos/$OWNER/$REPO/rulesets/$rid" -f enforcement=active >/dev/null \
        && echo "  ruleset $rid -> active" \
        || echo "  WARNING: failed to restore ruleset $rid — check manually: gh api repos/$OWNER/$REPO/rulesets/$rid"
    done < "$STATE_FILE"
  fi
}
trap restore_rulesets EXIT INT TERM

# --- Get base branch of the PR ----------------------------------------------
BASE_BRANCH=$(gh pr view "$PR_NUM" --repo "$OWNER/$REPO" --json baseRefName --jq '.baseRefName')
echo "Base branch: $BASE_BRANCH"

# --- Attempt 1: plain admin-bypass merge (handles classic branch protection) -
echo "Attempting admin-bypass merge..."
if gh pr merge "$PR_NUM" --repo "$OWNER/$REPO" "--$MERGE_METHOD" --admin 2>/tmp/gh-force-merge-err.txt; then
  echo "Merged successfully on first attempt."
  exit 0
fi

ERR=$(cat /tmp/gh-force-merge-err.txt)
echo "$ERR"

if ! grep -qi "rule violation" <<<"$ERR"; then
  echo "Merge failed for a reason unrelated to repository rulesets. Not retrying automatically."
  exit 1
fi

# --- Find active rulesets targeting the base branch and disable them -------
echo "Repository ruleset violation detected — locating blocking rulesets on '$BASE_BRANCH'..."
RULESET_IDS=$(gh api "repos/$OWNER/$REPO/rulesets" --jq '.[].id')

for rid in $RULESET_IDS; do
  detail=$(gh api "repos/$OWNER/$REPO/rulesets/$rid")
  enforcement=$(jq -r '.enforcement' <<<"$detail")
  target=$(jq -r '.target' <<<"$detail")
  matches_branch=$(jq -r --arg b "refs/heads/$BASE_BRANCH" \
    '(.conditions.ref_name.include // []) | index($b) != null or index("~ALL") != null' <<<"$detail")

  if [[ "$target" == "branch" && "$enforcement" == "active" && "$matches_branch" == "true" ]]; then
    echo "Disabling ruleset $rid ($(jq -r '.name' <<<"$detail"))..."
    gh api -X PUT "repos/$OWNER/$REPO/rulesets/$rid" -f enforcement=disabled >/dev/null
    echo "$rid" >> "$STATE_FILE"
  fi
done

if [[ ! -s "$STATE_FILE" ]]; then
  echo "No matching active branch rulesets found to disable. Cannot proceed automatically."
  exit 1
fi

# --- Attempt 2: retry admin-bypass merge now that blocking rulesets are off -
echo "Retrying admin-bypass merge..."
gh pr merge "$PR_NUM" --repo "$OWNER/$REPO" "--$MERGE_METHOD" --admin
echo "Merged successfully after temporarily disabling ruleset(s): $(tr '\n' ' ' < "$STATE_FILE")"
