#!/usr/bin/env bash
# lookup-app-role-assignment.sh
#
# Looks up the Graph API assignment ID needed to import an azuread_app_role_assignment resource.
#
# Usage:
#   bash lookup-app-role-assignment.sh <resource_object_id> <principal_object_id> [app_role_id]
#
# Arguments:
#   resource_object_id  - Object ID of the service principal that owns the app role
#                         (the resource_object_id field in the Terraform resource)
#   principal_object_id - Object ID of the user/group/SP that was assigned the role
#                         (the principal_object_id field in the Terraform resource)
#   app_role_id         - (Optional) Filter to a specific app role UUID
#
# Output:
#   Prints the ready-to-use terragrunt import command(s)
#
# Example:
#   bash lookup-app-role-assignment.sh \
#     d18a7e28-3814-4695-b79f-4d5ca8f6e8c9 \
#     fc03bbd1-329e-4b3c-ac4e-749ba2cdb379

set -euo pipefail

RESOURCE_OBJECT_ID="${1:-}"
PRINCIPAL_OBJECT_ID="${2:-}"
APP_ROLE_ID="${3:-}"

if [[ -z "$RESOURCE_OBJECT_ID" || -z "$PRINCIPAL_OBJECT_ID" ]]; then
  echo "Usage: $0 <resource_object_id> <principal_object_id> [app_role_id]" >&2
  exit 1
fi

echo "Looking up app role assignments for principal $PRINCIPAL_OBJECT_ID on SP $RESOURCE_OBJECT_ID..." >&2

if [[ -n "$APP_ROLE_ID" ]]; then
  FILTER="value[?principalId=='${PRINCIPAL_OBJECT_ID}' && appRoleId=='${APP_ROLE_ID}']"
else
  FILTER="value[?principalId=='${PRINCIPAL_OBJECT_ID}']"
fi

RESULTS=$(az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/servicePrincipals/${RESOURCE_OBJECT_ID}/appRoleAssignedTo" \
  --query "${FILTER}.{assignmentId:id,appRoleId:appRoleId,principalId:principalId}" \
  -o json 2>/dev/null)

COUNT=$(echo "$RESULTS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")

if [[ "$COUNT" -eq 0 ]]; then
  echo "ERROR: No matching app role assignment found." >&2
  echo "  resource_object_id:  $RESOURCE_OBJECT_ID" >&2
  echo "  principal_object_id: $PRINCIPAL_OBJECT_ID" >&2
  [[ -n "$APP_ROLE_ID" ]] && echo "  app_role_id:         $APP_ROLE_ID" >&2
  exit 1
fi

echo ""
echo "Found $COUNT assignment(s). Import ID(s):"
echo ""

echo "$RESULTS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data:
    aid = item['assignmentId']
    rid = item['appRoleId']
    pid = item['principalId']
    import_id = f'/servicePrincipals/${RESOURCE_OBJECT_ID}/appRoleAssignedTo/{aid}'
    print(f'  appRoleId: {rid}')
    print(f'  principalId: {pid}')
    print(f'  Import ID: {import_id}')
    print()
    print(f'  terragrunt import \\'azuread_app_role_assignment.RESOURCE_NAME[0]\\' \\'
    print(f'    \\'{import_id}\\'')
    print()
"
