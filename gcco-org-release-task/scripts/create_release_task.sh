#!/usr/bin/env bash
# create_release_task.sh — Create and close an ADO Task for a GCCO org release update.
#
# Usage:
#   ./create_release_task.sh <ORG_NAME> <RELEASE> [ESLZ_VERSION] [PARENT_ID] [--no-close]
#
# Examples:
#   ./create_release_task.sh DND-DICE 20260310.0
#   ./create_release_task.sh SSC-CloudOps-ESLZ 20260310.0 r3.2 3121
#   ./create_release_task.sh SSC-Aurora 20260310.0 r3.2 3121 --no-close

set -euo pipefail

ORG_NAME="${1:?Usage: $0 <ORG_NAME> <RELEASE> [ESLZ_VERSION] [PARENT_ID] [--no-close]}"
RELEASE="${2:?Release version required (e.g. 20260310.0)}"
ESLZ_VERSION="${3:-r3.2}"
PARENT_ID="${4:-3121}"
CLOSE_TASK=true
for arg in "$@"; do [[ "$arg" == "--no-close" ]] && CLOSE_TASK=false; done

AZDO_ORG="https://dev.azure.com/Azure163ent-CloudOperations"
PROJECT="Activities"
AREA="Activities\\Projects\\GCCO Releases"
ASSIGNED_TO="admin.bernard.maltais@ent.cloud-nuage.canada.ca"

echo "==> Finding current sprint..."
ITERATION=$(az boards iteration project list \
  --project "$PROJECT" \
  --org "$AZDO_ORG" \
  --depth 5 --output json | python3 -c "
import json, sys, re
from datetime import date, datetime
today = date.today()
data = json.load(sys.stdin)
results = []
def find_current(node, path=''):
    path = (path + '\\\\' + node['name']) if path else node['name']
    attrs = node.get('attributes') or {}
    start, finish = attrs.get('startDate'), attrs.get('finishDate')
    if start and finish:
        s = datetime.fromisoformat(start[:10]).date()
        f = datetime.fromisoformat(finish[:10]).date()
        if s <= today <= f and not node.get('children'):
            results.append(path)
            return
    for c in (node.get('children') or []):
        find_current(c, path)
find_current(data)
# Prefer paths directly under Projects\\FY (not Migration, GCCO Releases, etc.)
preferred = [p for p in results if re.search(r'Projects\\\\FY', p)]
print((preferred or results)[0] if (preferred or results) else '')
")

if [[ -z "$ITERATION" ]]; then
  echo "ERROR: Could not determine current sprint. Check az CLI auth." >&2
  exit 1
fi
echo "    Sprint: $ITERATION"

echo "==> Creating task..."
NEW_ID=$(az boards work-item create \
  --title "Update ${ORG_NAME} to release ${RELEASE}" \
  --type "Task" \
  --project "$PROJECT" \
  --org "$AZDO_ORG" \
  --area "$AREA" \
  --iteration "$ITERATION" \
  --description "In preparation for the project update to ESLZ ${ESLZ_VERSION} we need to update the ADO Org release to release ${RELEASE}." \
  --assigned-to "$ASSIGNED_TO" \
  --fields "Microsoft.VSTS.Common.Priority=2" \
  --output json | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "    Created task #${NEW_ID}"

echo "==> Linking to parent #${PARENT_ID}..."
az boards work-item relation add \
  --id "$NEW_ID" \
  --relation-type "Parent" \
  --target-id "$PARENT_ID" \
  --org "$AZDO_ORG" \
  --output none
echo "    Linked."

if $CLOSE_TASK; then
  echo "==> Closing task..."
  az boards work-item update \
    --id "$NEW_ID" \
    --state "Closed" \
    --org "$AZDO_ORG" \
    --output none
  echo "    Closed."
fi

echo ""
echo "Done! Task #${NEW_ID}: Update ${ORG_NAME} to release ${RELEASE}"
echo "URL: ${AZDO_ORG}/Activities/_workitems/edit/${NEW_ID}"
