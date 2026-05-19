# Terraform Import ID Formats — Azure

## General Rule

For most `azurerm_*` resources the import ID is the **full ARM resource ID**, which you can retrieve with:
```bash
az resource show --ids "/subscriptions/SUB/resourceGroups/RG/providers/PROVIDER/TYPE/NAME" --query id -o tsv
# or search by name:
az resource list --name RESOURCE_NAME --query "[].id" -o tsv
```

---

## azurerm_private_dns_zone

```
/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/privateDnsZones/{zone_name}
```
Example zone names: `privatelink.vaultcore.azure.net`, `privatelink.blob.core.windows.net`

Lookup:
```bash
az network private-dns zone list --subscription SUB_ID --query "[?name=='privatelink.vaultcore.azure.net'].id" -o tsv
```

---

## azurerm_private_dns_zone_virtual_network_link

```
/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/privateDnsZones/{zone_name}/virtualNetworkLinks/{link_name}
```

---

## azurerm_role_assignment

```
/subscriptions/{sub}[/resourceGroups/{rg}[/providers/{...}/{resource}]]/providers/Microsoft.Authorization/roleAssignments/{guid}
```

**The GUID is in the 409 error message** — it is a 32-char hex string with no dashes:
```
RoleAssignmentExists: The ID of the existing role assignment is 7b082443c50f63a247a6d8385d2edfe3
```
Reformat to UUID (8-4-4-4-12):
```
7b082443-c50f-63a2-47a6-d8385d2edfe3
         ^    ^    ^    ^
```

Lookup by scope + role if needed:
```bash
az role assignment list --scope SCOPE --query "[?roleDefinitionName=='Reader'].id" -o tsv
```

---

## azuread_app_role_assignment

**Cannot be derived from apply output.** Must query Graph API.

Format: `/servicePrincipals/{resource_object_id}/appRoleAssignedTo/{assignment_id}`

Where:
- `resource_object_id` = the SP whose app role is being assigned to (the application/SP, not the principal)
- `assignment_id` = a **base64-encoded** opaque string from Graph API

Lookup with:
```bash
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/servicePrincipals/{resource_object_id}/appRoleAssignedTo" \
  --query "value[?principalId=='{principal_object_id}'].id" \
  -o tsv
```
The returned value is the `assignment_id` to use directly in the import path.

---

## azurerm_key_vault

```
/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{name}
```

Lookup:
```bash
az keyvault list --subscription SUB_ID --query "[].id" -o tsv
```

---

## azurerm_resource_group

```
/subscriptions/{sub}/resourceGroups/{rg_name}
```

---

## azurerm_virtual_network

```
/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{name}
```

---

## azurerm_subnet

```
/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}/subnets/{subnet_name}
```

---

## azurerm_network_security_group

```
/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/networkSecurityGroups/{name}
```

---

## azurerm_storage_account

```
/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{name}
```

---

## azurerm_recovery_services_vault

```
/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.RecoveryServices/vaults/{name}
```

---

## azuread_group

Import by object ID:
```
{object_id}
```

Lookup:
```bash
az ad group show --group "Display Name" --query id -o tsv
```

---

## azuread_service_principal

Import by object ID:
```
{object_id}
```

---

## module.* resources

For resources inside modules, use the full Terraform address including module path:
```bash
terragrunt import 'module.rbac["Key Vault Secrets Officer"].azurerm_role_assignment.roles["PRINCIPAL-SCOPE"]' 'ARM_ID'
```
Quote the address carefully — spaces and special chars in map keys require quoting.
