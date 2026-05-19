---
name: terraform-import
description: 'Import existing Azure resources into Terraform/Terragrunt state. Use when: terraform apply fails with "already exists", "resource already exists", "RoleAssignmentExists", "Permission being assigned already exists", or any error indicating a resource exists outside of state. Handles azurerm_private_dns_zone, azurerm_role_assignment, azuread_app_role_assignment, and generic ARM resources. Supports both terraform import and terragrunt import.'
argument-hint: 'Paste the terraform apply error output'
---

# Terraform / Terragrunt Import Skill

## When to Use

- `terraform apply` or `terragrunt apply` fails with any of:
  - `"already exists - to be managed via Terraform this resource needs to be imported"`
  - `"RoleAssignmentExists: The role assignment already exists"`
  - `"Permission being assigned already exists on the object"` (azuread_app_role_assignment)
  - `"Conflict" / 409` on resource creation

## Procedure

### Step 1 — Parse the errors

From the error output, extract for each failing resource:
- The **Terraform resource address** (e.g. `azurerm_private_dns_zone.privatelink_vault[0]`)
- The **existing resource ID** if shown in the error message (e.g. role assignment GUIDs in 409 errors)
- The **resource type** to determine the correct import ID format

### Step 2 — Determine the import ID format

Consult [./references/import-id-formats.md](./references/import-id-formats.md) for the correct format per resource type.

Key rules:
- **ARM resources** (azurerm_*): import ID is the full Azure resource path `/subscriptions/.../providers/...`
- **azurerm_role_assignment**: import ID is `/subscriptions/.../providers/Microsoft.Authorization/roleAssignments/{guid}` — the GUID comes directly from the `409` error message
- **azuread_app_role_assignment**: import ID must be looked up via Graph API — NOT constructible from apply output alone. Run [./scripts/lookup-app-role-assignment.sh](./scripts/lookup-app-role-assignment.sh)

### Step 3 — Look up missing IDs

For `azurerm_role_assignment` 409 errors, the assignment ID is embedded in the error:
```
RoleAssignmentExists: The role assignment already exists. The ID of the existing role assignment is 7b082443c50f63a247a6d8385d2edfe3.
```
Reformat the hex string as a UUID: `7b082443-c50f-63a2-47a6-d8385d2edfe3` (insert dashes at positions 8-4-4-4-12).

For `azuread_app_role_assignment` 400 errors, run:
```bash
bash ~/.copilot/skills/terraform-import/scripts/lookup-app-role-assignment.sh \
  <resource_object_id> <principal_object_id>
```

### Step 4 — Run imports

Use `terragrunt import` when working inside a terragrunt project (presence of `terragrunt.hcl`), otherwise use `terraform import`.

```bash
# Generic pattern
terragrunt import '<terraform_resource_address>' '<import_id>'

# Example — private DNS zone
terragrunt import \
  'azurerm_private_dns_zone.privatelink_vault[0]' \
  '/subscriptions/SUB_ID/resourceGroups/RG_NAME/providers/Microsoft.Network/privateDnsZones/privatelink.vaultcore.azure.net'

# Example — role assignment (UUID from 409 error, reformatted with dashes)
terragrunt import \
  'module.rbac["Key Vault Secrets Officer"].azurerm_role_assignment.roles["PRINCIPAL_ID-SCOPE_NAME"]' \
  '/subscriptions/SUB_ID/.../providers/Microsoft.Authorization/roleAssignments/GUID'

# Example — azuread_app_role_assignment (ID from Graph API lookup)
terragrunt import \
  'azuread_app_role_assignment.f5_saml[0]' \
  '/servicePrincipals/SP_OBJECT_ID/appRoleAssignedTo/BASE64_ASSIGNMENT_ID'
```

### Step 5 — Re-run apply

After all imports succeed, re-run `tga` / `terragrunt apply` to confirm no remaining conflicts.

## Tips

- Run imports **one at a time** to catch failures early
- Role assignment GUIDs in 409 errors are hex strings without dashes — insert dashes at 8-4-4-4-12
- `azuread_app_role_assignment` import IDs are base64-encoded strings, not UUIDs
- If a `terragrunt import` overwrites the cache, re-run `terragrunt init` before the next import
