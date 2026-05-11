# Backward Compatibility Patterns

Use when: planning any change — verify the pattern preserves existing tfvars.
**Rule:** Existing tfvars must produce an identical plan before and after the upgrade.

---

## Pattern 1 — Single object OR list normalization

```hcl
# locals.tf — normalize image_registry_credentials to list regardless of caller format
# WRONG: can(tolist(raw)) ? raw : [raw]  — both branches must have consistent types
_image_registry_credentials_raw = try(var.container_group.image_registry_credentials, [])
image_registry_credentials = try(
  tolist(local._image_registry_credentials_raw),
  [local._image_registry_credentials_raw]   # single object fallback
)
```

```hcl
dynamic "image_registry_credential" {
  for_each = local.image_registry_credentials
  content {
    server                    = image_registry_credential.value.server
    username                  = try(image_registry_credential.value.username, null)
    password                  = try(image_registry_credential.value.password, null)
    user_assigned_identity_id = try(image_registry_credential.value.user_assigned_identity_id, null)
  }
}
```

## Pattern 2 — Making a required block optional

```hcl
# Before: dns_config { nameservers = var... }  — always emitted, breaks when dns_config absent
# After: dynamic — existing callers that supply dns_config still work; no state change
dynamic "dns_config" {
  for_each = try(var.container_group.dns_config, null) != null ? [1] : []
  content {
    nameservers    = var.container_group.dns_config.nameservers
    search_domains = try(var.container_group.dns_config.search_domains, null)
    options        = try(var.container_group.dns_config.options, null)
  }
}
```

## Pattern 3 — Conditional required argument

```hcl
# subnet_ids must be absent when ip_address_type = "None"
# locals.tf
subnet_id = try(var.container_group.subnet, null) != null ? (
  strcontains(var.container_group.subnet, "/resourceGroups/") ? var.container_group.subnet : var.subnets[var.container_group.subnet].id
) : null

# module.tf
subnet_ids = local.subnet_id != null ? [local.subnet_id] : null
```

## Pattern 4 — Single port → multi-port with backward compat

```hcl
# Old callers: port = 80, protocol = "TCP"  (singular keys)
# New callers: ports = [{ port = 80, protocol = "TCP" }]  (list)
dynamic "ports" {
  for_each = try(
    container.value["ports"],                          # new list format wins if present
    try(container.value["port"], null) != null         # fall back to old singular keys
      ? [{ port = container.value["port"], protocol = try(container.value["protocol"], "TCP") }]
      : []
  )
  content {
    port     = ports.value["port"]
    protocol = try(ports.value["protocol"], "TCP")
  }
}
```

## Pattern 5 — Optional argument with try()

```hcl
# All new optional arguments — simply add with try(..., null); null → provider ignores arg; no plan diff
dns_name_label                      = try(var.container_group.dns_name_label, null)
dns_name_label_reuse_policy         = try(var.container_group.dns_name_label_reuse_policy, null)
key_vault_key_id                    = try(var.container_group.key_vault_key_id, null)
key_vault_user_assigned_identity_id = try(var.container_group.key_vault_user_assigned_identity_id, null)
zones                               = try(var.container_group.zones, null)
```

## Pattern 6 — `moved` blocks (resource address changes)

```hcl
# moved.tf — use when: resource renamed, moved to/from module, or count/for_each key changes
# do NOT use for: argument-only changes or new optional dynamic blocks
moved {
  from = azurerm_container_group.old_name
  to   = azurerm_container_group.container_group
}
```

## Pattern 7 — Regex escape sequences

```hcl
# Terraform uses RE2. \/ is NOT a valid escape — forward slash never needs escaping
# WRONG — "Invalid escape sequence" error
regex("[^\/]+$", var.resource_id)
# CORRECT
regex("[^/]+$", var.resource_id)
```

## Pattern 8 — Sensitive outputs

```hcl
# terraform test with mock_provider fails if output exposes sensitive nested attrs without sensitive = true
output "container_group" {
  description = "Container group object"
  value       = azurerm_container_group.container_group
  sensitive   = true
}
```

## Pattern 9 — environment_variables missing try()

```hcl
# WRONG — crashes if container object has no "environment_variables" key
environment_variables = merge(container.value["environment_variables"], var.extra_env_vars)
# CORRECT
environment_variables = merge(try(container.value["environment_variables"], {}), var.extra_env_vars)
```

## Pattern 10 — Naming convention backward compat (three-tier fallback)

```hcl
# Use when git log shows a prior commit changed the naming formula
# Without this: existing resources get destroyed + recreated (Terraform state diff on name)
locals {
  # Priority 1: explicit override (migration escape hatch)
  # Priority 2: legacy formula (fires only when old discriminator vars present)
  # Priority 3: new ESLZ convention (default for all new deployments)
  resource-name = try(
    var.resource_config.name,
    var.group != null && var.project != null
      ? "${var.env}-${var.group}-${var.project}-${var.userDefinedString}"
      : "${var.env}SLD-${var.userDefinedString}-ci"
  )
}
```

```hcl
# Test all three branches:
run "legacy_naming" {
  command = plan
  variables { group = "OPS", project = "CORE" }
  assert { condition = resource.name == "DEV-OPS-CORE-myapp", error_message = "Legacy naming must be preserved when group+project supplied" }
}
run "new_naming" {
  command = plan
  assert { condition = resource.name == "DEVSLD-myapp-ci", error_message = "New ESLZ naming must apply when group+project absent" }
}
run "explicit_name_override" {
  command = plan
  variables { resource_config = { name = "existing-prod-name" } }
  assert { condition = resource.name == "existing-prod-name", error_message = "Explicit name must take priority" }
}
```

## Pattern 11 — Restoring removed module variables

```hcl
# Use when a prior commit removed input vars; callers passing them fail plan with "Unsupported argument"
# NEVER remove a module input variable that any caller is known to pass
variable "group" {
  description = "(Optional) Legacy group value — retained for backward compatibility"
  type        = string
  default     = null   # callers that omit it are unaffected
}
variable "project" {
  description = "(Optional) Legacy project value — retained for backward compatibility"
  type        = string
  default     = null
}
# Can be used in Pattern 10 naming fallback or simply accepted and ignored
```

## Pattern 12 — Optional name override for every auto-generated resource name

Use when: upgrading or creating any module that auto-generates resource names. Every
`name = "${local.prefix}-suffix"` must accept an optional caller-supplied override so that
existing deployments whose names diverge from the formula can be managed without destroy/recreate.

**Applies to:** VM, OS disk, NIC, NIC IP configuration, data disks, NSG, Key Vault secret,
and any other resource whose name is constructed from locals.

```hcl
# module.tf — VM
resource "azurerm_windows_virtual_machine" "vm" {
  name = try(var.windows_VM.vm_name, local.vm-name)   # override: vm_name = "existing-prod-vm"
  ...
  os_disk {
    name = try(var.windows_VM.os_disk.name, "${local.vm-name}-osdisk1")
  }
}

# NIC resource — override lives inside the per-NIC object
resource "azurerm_network_interface" "vm-nic" {
  for_each = var.windows_VM.nic
  name     = try(each.value.name, "${local.vm-name}-nic${local.nic_indices[each.key] + 1}")

  ip_configuration {
    name = try(each.value.ip_configuration_name, "${local.vm-name}-ipconfig${local.nic_indices[each.key] + 1}")
  }
}

# Data disk — override lives inside the per-disk object
resource "azurerm_managed_disk" "data_disks" {
  for_each = try(var.windows_VM.data_disks, {})
  name     = try(each.value.name, "${local.vm-name}-datadisk${each.value.lun + 1}")
}

# NSG — top-level override
resource "azurerm_network_security_group" "NSG" {
  count = try(var.windows_VM.use_nic_nsg, false) ? 1 : 0
  name  = try(var.windows_VM.nsg_name, "${local.vm-name}-nsg")
}

# Key Vault secret — top-level override
resource "azurerm_key_vault_secret" "vm-admin-password" {
  count = try(var.windows_VM.admin_password, "") == "" ? 1 : 0
  name  = try(var.windows_VM.kv_secret_name, "${local.vm-name}-vm-admin-password")
}

# Association resources: align ip_configuration_name with the NIC override
resource "azurerm_network_interface_backend_address_pool_association" "LB" {
  for_each              = try(var.windows_VM.load_balancer_address_pools_ids, {})
  ip_configuration_name = try(var.windows_VM.nic[keys(local.nic_indices)[0]].ip_configuration_name, "${local.vm-name}-ipconfig1")
}
```

**tftest assertion pattern:**

```hcl
run "custom_resource_names" {
  command = plan
  variables {
    windows_VM = {
      vm_name        = "my-existing-vm"
      nsg_name       = "my-existing-nsg"
      kv_secret_name = "my-existing-secret"
      os_disk        = { name = "my-existing-osdisk" }
      nic = {
        nic1 = {
          name                  = "my-existing-nic"
          ip_configuration_name = "my-existing-ipconfig"
          subnet                = "OZ"
          private_ip_address_allocation = "Dynamic"
        }
      }
      # ... other required fields ...
    }
  }
  assert { condition = azurerm_windows_virtual_machine.vm.name == "my-existing-vm", error_message = "vm_name override not applied" }
  assert { condition = azurerm_windows_virtual_machine.vm.os_disk[0].name == "my-existing-osdisk", error_message = "os_disk.name override not applied" }
  assert { condition = azurerm_network_interface.vm-nic["nic1"].name == "my-existing-nic", error_message = "nic.name override not applied" }
  assert { condition = azurerm_network_interface.vm-nic["nic1"].ip_configuration[0].name == "my-existing-ipconfig", error_message = "ip_configuration_name override not applied" }
  assert { condition = azurerm_network_security_group.NSG[0].name == "my-existing-nsg", error_message = "nsg_name override not applied" }
}
```

**ESLZ tfvars documentation pattern (add as commented lines near each resource section):**

```hcl
# vm_name        = ""  # Optional: Override the auto-generated VM name (default: {env4}{serverType3}-{userDefinedString7})
# nsg_name       = ""  # Optional: Override the auto-generated NSG name (default: <vm-name>-nsg)
# kv_secret_name = ""  # Optional: Override the Key Vault secret name (default: <vm-name>-vm-admin-password)

nic = {
  nic1 = {
    # name                  = ""  # Optional: Override the auto-generated NIC name (default: <vm-name>-nicN)
    # ip_configuration_name = ""  # Optional: Override the NIC IP configuration name (default: <vm-name>-ipconfigN)
  }
}
os_disk = {
  # name = ""  # Optional: Override the auto-generated OS disk name (default: <vm-name>-osdisk1)
}
data_disks = {
  disk1 = {
    # name = ""  # Optional: Override the auto-generated data disk name (default: <vm-name>-datadiskN where N = lun+1)
  }
}
```

