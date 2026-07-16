#!/usr/bin/env bash
# ado-list-tagged-items.sh — List open Azure DevOps work items carrying a given tag.
#
# Usage: ado-list-tagged-items.sh <org> <project> <tag>
#
# Wraps: az boards query --wiql "..." for open items tagged <tag>.
# Prints a JSON array of {"id": <int>, "title": <string>} objects to stdout on success.

set -euo pipefail

ORG="${1:?Usage: ado-list-tagged-items.sh <org> <project> <tag>}"
PROJECT="${2:?Usage: ado-list-tagged-items.sh <org> <project> <tag>}"
TAG="${3:?Usage: ado-list-tagged-items.sh <org> <project> <tag>}"

if ! az extension list -o tsv --query "[?name=='azure-devops'].name" 2>/dev/null | grep -q azure-devops; then
  echo "==> Installing azure-devops CLI extension..." >&2
  az extension add --name azure-devops -y >&2
fi

WIQL="SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.TeamProject] = '${PROJECT}' AND [System.Tags] CONTAINS '${TAG}' AND [System.State] <> 'Closed' AND [System.State] <> 'Removed'"

echo "==> Querying work items tagged '${TAG}'..." >&2

if ! RAW=$(az boards query --org "$ORG" --wiql "$WIQL" -o json 2>&1); then
  echo "ado-list-tagged-items: az boards query failed: ${RAW}" >&2
  exit 1
fi

# az boards query prints nothing at all (not "[]") when zero work items match.
if [[ -z "${RAW// /}" ]]; then
  RAW="[]"
fi

python3 -c "
import json, sys
d = json.loads(sys.argv[1])
items = d if isinstance(d, list) else d.get('workItems', [])
out = [{'id': i['id'], 'title': i['fields']['System.Title']} for i in items]
print(json.dumps(out))
" "$RAW"
