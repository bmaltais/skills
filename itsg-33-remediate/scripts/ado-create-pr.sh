#!/usr/bin/env bash
# ado-create-pr.sh — Open a draft Azure DevOps PR linked to a work item.
#
# Usage: ado-create-pr.sh <org> <project> <repo> <source-branch> <title> <body-file> <work-item-id> [<target-branch>]
#   When <target-branch> is omitted, the repo's default branch is auto-detected.
#
# Wraps: az repos pr create --draft --work-items <work-item-id>
# Prints "<id> <url>" to stdout on success.

set -euo pipefail

ORG="${1:?Usage: ado-create-pr.sh <org> <project> <repo> <source-branch> <title> <body-file> <work-item-id> [<target-branch>]}"
PROJECT="${2:?Usage: ado-create-pr.sh <org> <project> <repo> <source-branch> <title> <body-file> <work-item-id> [<target-branch>]}"
REPO="${3:?Usage: ado-create-pr.sh <org> <project> <repo> <source-branch> <title> <body-file> <work-item-id> [<target-branch>]}"
SOURCE_BRANCH="${4:?Usage: ado-create-pr.sh <org> <project> <repo> <source-branch> <title> <body-file> <work-item-id> [<target-branch>]}"
TITLE="${5:?Usage: ado-create-pr.sh <org> <project> <repo> <source-branch> <title> <body-file> <work-item-id> [<target-branch>]}"
BODY_FILE="${6:?Usage: ado-create-pr.sh <org> <project> <repo> <source-branch> <title> <body-file> <work-item-id> [<target-branch>]}"
WORK_ITEM_ID="${7:?Usage: ado-create-pr.sh <org> <project> <repo> <source-branch> <title> <body-file> <work-item-id> [<target-branch>]}"
TARGET_BRANCH="${8:-}"

if [[ ! -f "$BODY_FILE" ]]; then
  echo "ado-create-pr: body file not found: ${BODY_FILE}" >&2
  exit 1
fi

if ! az extension list -o tsv --query "[?name=='azure-devops'].name" 2>/dev/null | grep -q azure-devops; then
  echo "==> Installing azure-devops CLI extension..." >&2
  az extension add --name azure-devops -y >&2
fi

if [[ -z "$TARGET_BRANCH" ]]; then
  echo "==> Detecting default branch for ${REPO}..." >&2
  if ! TARGET_BRANCH=$(az repos show --org "$ORG" --project "$PROJECT" --repository "$REPO" --query defaultBranch -o tsv 2>&1); then
    echo "ado-create-pr: az repos show failed: ${TARGET_BRANCH}" >&2
    exit 1
  fi
  TARGET_BRANCH="${TARGET_BRANCH#refs/heads/}"
  if [[ -z "$TARGET_BRANCH" ]]; then
    echo "ado-create-pr: could not determine default branch for ${REPO}" >&2
    exit 1
  fi
fi

DESCRIPTION=$(cat "$BODY_FILE")

echo "==> Creating draft PR '${TITLE}' (${SOURCE_BRANCH} -> ${TARGET_BRANCH})..." >&2

if ! RAW=$(az repos pr create \
  --org "$ORG" \
  --project "$PROJECT" \
  --repository "$REPO" \
  --source-branch "$SOURCE_BRANCH" \
  --target-branch "$TARGET_BRANCH" \
  --title "$TITLE" \
  --description "$DESCRIPTION" \
  --work-items "$WORK_ITEM_ID" \
  --draft \
  -o json 2>&1); then
  echo "ado-create-pr: az repos pr create failed: ${RAW}" >&2
  exit 1
fi

python3 -c "
import json, sys
d = json.loads(sys.argv[1])
org = sys.argv[2]
project = sys.argv[3]
repo = sys.argv[4]
print(d['pullRequestId'], org + '/' + project + '/_git/' + repo + '/pullrequest/' + str(d['pullRequestId']))
" "$RAW" "$ORG" "$PROJECT" "$REPO"
