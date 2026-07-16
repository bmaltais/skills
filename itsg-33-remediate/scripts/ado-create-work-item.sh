#!/usr/bin/env bash
# ado-create-work-item.sh — Create an Azure DevOps work item with tags.
#
# Usage: ado-create-work-item.sh <org> <project> <type> <title> <tags> <description-file>
#   <tags> is a semicolon-separated string, e.g. "itsg-33:gap; P1"
#
# Wraps: az boards work-item create --type <type> --title <title> \
#          --description <html> --fields "System.Tags=<tags>"
# Prints "<id> <url>" to stdout on success.

set -euo pipefail

ORG="${1:?Usage: ado-create-work-item.sh <org> <project> <type> <title> <tags> <description-file>}"
PROJECT="${2:?Usage: ado-create-work-item.sh <org> <project> <type> <title> <tags> <description-file>}"
TYPE="${3:?Usage: ado-create-work-item.sh <org> <project> <type> <title> <tags> <description-file>}"
TITLE="${4:?Usage: ado-create-work-item.sh <org> <project> <type> <title> <tags> <description-file>}"
TAGS="${5:?Usage: ado-create-work-item.sh <org> <project> <type> <title> <tags> <description-file>}"
DESCRIPTION_FILE="${6:?Usage: ado-create-work-item.sh <org> <project> <type> <title> <tags> <description-file>}"

if [[ ! -f "$DESCRIPTION_FILE" ]]; then
  echo "ado-create-work-item: description file not found: ${DESCRIPTION_FILE}" >&2
  exit 1
fi

if ! az extension list -o tsv --query "[?name=='azure-devops'].name" 2>/dev/null | grep -q azure-devops; then
  echo "==> Installing azure-devops CLI extension..." >&2
  az extension add --name azure-devops -y >&2
fi

DESCRIPTION=$(cat "$DESCRIPTION_FILE")

echo "==> Creating work item '${TITLE}'..." >&2

if ! RAW=$(az boards work-item create \
  --org "$ORG" \
  --project "$PROJECT" \
  --type "$TYPE" \
  --title "$TITLE" \
  --description "$DESCRIPTION" \
  --fields "System.Tags=${TAGS}" \
  -o json 2>&1); then
  echo "ado-create-work-item: az boards work-item create failed: ${RAW}" >&2
  exit 1
fi

python3 -c "
import json, sys
d = json.loads(sys.argv[1])
org = sys.argv[2]
project = sys.argv[3]
print(d['id'], org + '/' + project + '/_workitems/edit/' + str(d['id']))
" "$RAW" "$ORG" "$PROJECT"
