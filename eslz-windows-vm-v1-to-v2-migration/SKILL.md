---
agents:
    - copilot
categories:
    - software-development
description: Migrate a Windows VM from the legacy `windows_VMs` module (list-based, v1) to the modern `windows_VMsV2` module (map-based, v2) in an ESLZ L1 or L2 blueprint, including config translation, state moves, and nic-nsg cleanup — without destroying the VM. Use when a plan shows `azurerm_windows_virtual_machine.VM must be replaced` due to attributes not supported by the old module (e.g. `vtpm_enabled`, `secure_boot_enabled`, `timezone`), or when the user asks to migrate a VM from windows_VMs to windows_VMsV2.
license: MIT
metadata:
    github-path: eslz-windows-vm-v1-to-v2-migration
    github-ref: refs/tags/v1.0.0
    github-repo: https://github.com/bmaltais/skills
    github-tree-sha: d15022dd94b59b846a05bb2b7d2cc73a64299dff
    scope: global
    source: custom
name: eslz-windows-vm-v1-to-v2-migration
---
# ESLZ Windows VM v1 → v2 Migration

Migrates an existing Azure VM from the legacy `windows_VMs` module to `windows_VMsV2` without
destroying and recreating the VM. This is needed when the old module lacks support for attributes
required to prevent forced replacement (e.g. `vtpm_enabled`, `secure_boot_enabled`, `timezone`).

## Hard rules

- Never run `terraform apply`, `terragrunt apply`, `terraform destroy`, or `terragrunt destroy` unless explicitly instructed.
- Use `terraform state mv` and `terraform state rm` **directly in the `.terragrunt-cache` working directory**, not via `terragrunt state` — Terragrunt will fail to parse `.hcl` files mid-migration if the generate block or inputs block is malformed.
- Never add a closing `}` to the `inputs = {` block in `terragrunt.hcl` — existing repos intentionally leave it open (it is closed by the root HCL include).
- Terragrunt `generate` blocks with heredoc (`<<EOF`) syntax **fail to parse** in most ESLZ repo versions. Use a `moved.tf` file placed directly in the `.terragrunt-cache` working directory as an alternative, or perform all moves via `terraform state mv`.
- Always verify the exact resource addresses in state with `terragrunt state list` (or `terraform state list` from the cache dir) before writing move commands.

## Step 1: Identify the forced-replacement cause

Read the `terraform plan` output carefully. The only lines that matter are marked `# forces replacement`. Common causes when migrating to V2:

| Attribute | Root cause | Fix |
|---|---|---|
| `vtpm_enabled = true -> null` | Old module ignores this; V2 reads it from config | Add `vtpm_enabled = true` to V2 config |
| `secure_boot_enabled = true -> null` | Same as above | Add `secure_boot_enabled = true` to V2 config |
| `timezone = "UTC-11"` added | V2 module defaults `timezone = "UTC-11"` but old VMs had none set | Add `timezone = null` to V2 config to suppress the default |

Also check for non-forced changes that indicate the old module didn't pass attributes at all — these confirm that the V2 config entry needs explicit overrides.

## Step 2: Discover current state addresses

```bash
# From the landing zone layer directory (e.g. prod/L1_blueprint_base)
terragrunt state list 2>/dev/null | grep "windows_VMs\|windows_VMsV2"
```

For a VM with key `SWJ-RDS02` in the old module, expect:

```
module.windows_VMs["SWJ-RDS02"].azurerm_network_interface.NIC
module.windows_VMs["SWJ-RDS02"].azurerm_network_interface_security_group_association.nic-nsg[0]
module.windows_VMs["SWJ-RDS02"].azurerm_network_security_group.NSG[0]
module.windows_VMs["SWJ-RDS02"].azurerm_windows_virtual_machine.VM
```

Note: `windows_VMsV2` NIC key names match the keys in the `nic = {}` block (e.g. `nic1`).

## Step 3: Determine the old module key

The old `windows_VMs` module builds its for_each key from:

```
"${serverType}-${userDefinedString}${postfix}"
```

Example: `serverType = "SWJ"`, `userDefinedString = "RDS"`, `postfix = "02"` → key `"SWJ-RDS02"`.

The V2 module key is just the map key in `windows_VMsV2 = { <KEY> = { ... } }` (e.g. `"RDS02"`).

## Step 4: Add the VM to SRV-WindowsV2.tfvars

Add a new entry to `config/SRV-WindowsV2.tfvars`. Translate from the old list entry.

**Key attribute mapping (old → new):**

| Old (`windows_VMs` list item) | New (`windows_VMsV2` map entry) |
|---|---|
| `serverType`, `userDefinedString`, `postfix` | Map key only (e.g. `RDS02`); `serverType` kept as-is |
| `subnet` (string) | Moved inside `nic = { nic1 = { subnet = "..." } }` |
| `private_ip_address_host` | `nic.nic1.private_ip_address` + `private_ip_address_allocation = "Static"` |
| `storage_os_disk` | `os_disk = { caching, storage_account_type, disk_size_gb, write_accelerator_enabled }` |
| `public_ip = false` | Omit (default) |
| `encryptDisks = false` | Omit (default) |
| *(ip configuration name implicit in old module as `ipconfig1`)* | `nic.nic1.ip_configuration_name = "ipconfig1"` — **always set this** (see note below) |

**Always include these override attributes to prevent forced replacement:**

```hcl
secure_boot_enabled = true   # if the VM was deployed with secure boot
vtpm_enabled        = true   # if the VM was deployed with vTPM
timezone            = null   # always set null to suppress the V2 default of "UTC-11"
disable_backup      = true   # if the VM has secure_boot_enabled + vtpm_enabled (Trusted Launch); the V2 module uses azurerm_backup_protected_vm which only supports standard policy; Trusted Launch VMs require Enhanced policy and will fail with UserErrorThisVMBackupIsSupportedUsingEnhancedPolicy
```

> **NIC ip_configuration name:** The old module always named the IP configuration `ipconfig1`. The V2 module defaults to `${vm-name}-ipconfig1` (e.g. `GcPcSWJ-RDS02-ipconfig1`). Azure **does not allow renaming or deleting a primary IP configuration** and will return `400 IpConfigDeleteNotSupported` on apply. Always set `ip_configuration_name = "ipconfig1"` on every NIC for migrated VMs. The upstream module does not support this attribute yet — see the upstream fix spec at the end of this document.

**If `use_nic_nsg = true`, also include:**

```hcl
use_nic_nsg    = true
security_rules = []   # required by the module even when no rules are needed
```

**Full example entry:**

```hcl
windows_VMsV2 = {
  RDS02 = {
    serverType           = "SWJ"
    resource_group       = "Management"
    admin_username       = "azureadmin"
    os_managed_disk_type = "StandardSSD_LRS"
    vm_size              = "Standard_D4ads_v5"

    enable_automatic_updates = true
    patch_assessment_mode    = "AutomaticByPlatform"
    patch_mode               = "AutomaticByPlatform"
    secure_boot_enabled      = true   # Required: VM deployed with secure boot; removing forces replacement
    vtpm_enabled             = true   # Required: VM deployed with vTPM; removing forces replacement
    timezone                 = null   # Required: suppress V2 default "UTC-11" which forces replacement
    disable_backup           = true   # Required: Trusted Launch (secure boot + vTPM) requires Enhanced backup policy; standard policy fails
    use_nic_nsg              = true   # Required: keep existing NIC-attached NSG managed
    security_rules           = []     # Required when use_nic_nsg = true

    nic = {
      nic1 = {
        subnet                        = "MAZ"
        private_ip_address_allocation = "Static"
        private_ip_address            = "10.x.x.x"
        ip_configuration_name         = "ipconfig1"  # Required: preserve Azure's existing ipconfig name; V2 default renames it causing apply failure
      }
    }

    storage_image_reference = {
      publisher = "MicrosoftWindowsServer"
      offer     = "WindowsServer"
      sku       = "2022-Datacenter-g2"
      version   = "latest"
    }
  }
}
```

## Step 5: Disable the VM in module.tfvars

Set `deploy = false` on the old list entry in `config/module.tfvars`. Do **not** delete it — keeping it commented with an explanation preserves history.

```hcl
{
  deploy                  = false # migrated to windows_VMsV2["RDS02"] in SRV-WindowsV2.tfvars
  serverType              = "SWJ"
  userDefinedString       = "RDS"
  postfix                 = "02"
  ...
}
```

## Step 6: Remove the nic-nsg association from state

The V2 module has no `azurerm_network_interface_security_group_association` resource — it attaches the NSG differently. Remove the old association from state so it is not destroyed on apply (the association remains in Azure).

```bash
# Use terraform directly in the cache dir — terragrunt state rm may fail during migration
CACHE=$(find <layer-dir>/.terragrunt-cache -name "*.tf" -not -path "*/.terraform/*" | head -1 | xargs dirname)
cd "$CACHE"

terraform state rm 'module.windows_VMs["SWJ-RDS02"].azurerm_network_interface_security_group_association.nic-nsg[0]'
```

## Step 7: Move the remaining resources in state

Run from the same cache directory:

```bash
# VM
terraform state mv \
  'module.windows_VMs["SWJ-RDS02"].azurerm_windows_virtual_machine.VM' \
  'module.windows_VMsV2["RDS02"].azurerm_windows_virtual_machine.vm'

# NIC (nic key must match the key in the nic = {} block, e.g. "nic1")
terraform state mv \
  'module.windows_VMs["SWJ-RDS02"].azurerm_network_interface.NIC' \
  'module.windows_VMsV2["RDS02"].azurerm_network_interface.vm-nic["nic1"]'

# NSG (count index [0] preserved in both modules)
terraform state mv \
  'module.windows_VMs["SWJ-RDS02"].azurerm_network_security_group.NSG[0]' \
  'module.windows_VMsV2["RDS02"].azurerm_network_security_group.NSG[0]'
```

If the VM also had data disks or a backup protected VM in state, move those too:

```bash
# Data disk (lun-based key in V2)
terraform state mv \
  'module.windows_VMs["SWJ-RDS02"].azurerm_managed_disk.data_disks["disk1"]' \
  'module.windows_VMsV2["RDS02"].azurerm_managed_disk.data_disks["disk1"]'

# Backup
terraform state mv \
  'module.windows_VMs["SWJ-RDS02"].azurerm_backup_protected_vm.backup_vm' \
  'module.windows_VMsV2["RDS02"].azurerm_backup_protected_vm.backup_vm[0]'
```

## Step 8: Validate the plan

```bash
cd <layer-dir>
terragrunt plan 2>&1 | grep -E "must be replaced|forces replacement|will be destroyed|Plan:"
```

A successful migration shows:
- No `must be replaced` for the migrated VM
- No `forces replacement`
- The VM shows as unchanged or with in-place updates only (`~`)

If a forced replacement still appears, re-read the plan output and check:
1. Is there a new `# forces replacement` attribute not covered in Step 2?
2. Does the moved resource address exactly match what `terragrunt state list` shows?
3. Does the V2 config entry have `timezone = null`?

## Troubleshooting

### `terragrunt state list` / `terragrunt state rm` fails with HCL parse error

Terragrunt parses `terragrunt.hcl` before delegating to Terraform. If the file has a syntax issue (e.g. an extra `}` on the `inputs` block, or a `generate` block with unsupported content), use Terraform directly:

```bash
CACHE=$(find <layer-dir>/.terragrunt-cache -maxdepth 4 -name "*.tf" -not -path "*/.terraform/*" | head -1 | xargs dirname)
cd "$CACHE"
terraform state list | grep "windows_VMs"
```

### The `inputs = {}` block in terragrunt.hcl must NOT have a closing `}`

ESLZ repos use a root HCL include that merges inputs. The `inputs = {` block is intentionally left unclosed in child `terragrunt.hcl` files. Compare with a working sibling layer to confirm the pattern.

### `generate` block with heredoc fails

Terragrunt `generate` blocks require the `contents` value to be a plain HCL string. Heredocs (`<<EOF`) are not reliably supported in all versions used by these repos. Use `terraform state mv` directly instead of trying to generate a `moved.tf`.

### `security_rules` attribute missing error

When `use_nic_nsg = true`, the V2 module iterates `var.windows_VM.security_rules` even if the NSG has no rules. Always include `security_rules = []` alongside `use_nic_nsg = true`.

### `UserErrorThisVMBackupIsSupportedUsingEnhancedPolicy` on apply

Azure VMs deployed with Trusted Launch (both `secure_boot_enabled = true` and `vtpm_enabled = true`) require an **Enhanced** backup policy. The `azurerm_backup_protected_vm` resource only supports standard policies and will fail:

```
Code="UserErrorThisVMBackupIsSupportedUsingEnhancedPolicy"
Message="This VM backup cannot be configured using standard policy, please use Enhanced Policy"
```

The existing backup in Azure is already protected by the Enhanced policy (set up outside Terraform). Set `disable_backup = true` in the V2 config to skip the `azurerm_backup_protected_vm` resource entirely. The backup protection remains intact in Azure — Terraform just stops managing the registration.

> **Important:** if this error occurs mid-apply, check whether `azurerm_backup_protected_vm.backup_vm[0]` landed in state before the failure. If it did, remove it: `terraform state rm 'module.windows_VMsV2["RDS02"].azurerm_backup_protected_vm.backup_vm[0]'`

### Attribute corruption from multi-line edits

When adding multiple new attributes to a V2 config block using an automated tool, verify each attribute is on its own line before running apply. A common failure mode is multiple attributes being concatenated onto a single line (e.g. `timezone = null  disable_backup = true  use_nic_nsg = true`), which HCL silently treats as a single broken assignment. Detect with:

```bash
python3 -c "
import re, sys
for i, line in enumerate(open('config/SRV-WindowsV2.tfvars'), 1):
    if re.search(r'= .+  \w+ =', line):
        print(f'Line {i} may have concatenated attributes: {line.rstrip()}')
"
```

### `timezone` forces replacement

The V2 module defaults `timezone = "UTC-11"`. If the existing VM was deployed without a timezone (old module ignores this attribute), Terraform sees a diff. Set `timezone = null` in the V2 config to let Azure keep whatever is currently set.

### `400 IpConfigDeleteNotSupported` on apply

The V2 module generates the NIC ip_configuration name as `${vm-name}-ipconfig${index+1}`. The old module always used the bare name `ipconfig1`. Azure refuses to rename a primary IP configuration, returning:

```
Error: updating Network Interface ... IpConfigDeleteNotSupported:
IP Configuration ipconfig1 cannot be deleted.
Deletion and renaming of primary IP Configuration is not supported
```

Fix: patch the cached module and add `ip_configuration_name` to the tfvars entry (workaround until upstream is fixed):

```bash
# Patch the cached module to accept an override
CACHE=$(find <layer-dir>/.terragrunt-cache -name "module.tf" -path "*/windows_VMsV2/*" | head -1)
sed -i 's/name.*=.*"${local.vm-name}-ipconfig${local.nic_indices\[each.key\] + 1}"/name = try(each.value.ip_configuration_name, "${local.vm-name}-ipconfig${local.nic_indices[each.key] + 1}")/' "$CACHE"
```

Or edit manually — change line:
```hcl
# Before
name = "${local.vm-name}-ipconfig${local.nic_indices[each.key] + 1}"
# After
name = try(each.value.ip_configuration_name, "${local.vm-name}-ipconfig${local.nic_indices[each.key] + 1}")
```

Then set in the NIC config:
```hcl
nic1 = {
  ...
  ip_configuration_name = "ipconfig1"  # preserve the Azure-side name
}
```

> **Cache caveat:** this patch lives only in `.terragrunt-cache` and is overwritten by the next `terragrunt init`. The permanent fix is an upstream module change (see spec below).

---

## Upstream module fix spec: `ip_configuration_name` override

This spec is ready to submit as a PR to the `windows_VMsV2` module repository.

### Problem

When migrating a VM from `windows_VMs` (v1) to `windows_VMsV2` (v2), the NIC ip_configuration name changes from `ipconfig1` (v1 hardcoded) to `${vm-name}-ipconfig1` (v2 default). Azure refuses to rename or delete a primary IP configuration, causing `400 IpConfigDeleteNotSupported` on apply.

### Change required in `module.tf`

In the `azurerm_network_interface.vm-nic` resource, `ip_configuration` block:

```hcl
# Current (line ~176)
ip_configuration {
  name = "${local.vm-name}-ipconfig${local.nic_indices[each.key] + 1}"

# Proposed
ip_configuration {
  name = try(each.value.ip_configuration_name, "${local.vm-name}-ipconfig${local.nic_indices[each.key] + 1}")
```

Also update the `azurerm_network_interface_backend_address_pool_association.LB` reference if it hard-codes `ipconfig1` — verify it reads from the NIC resource, not a literal.

### No variable change required

The `each.value` object already accepts arbitrary keys via `any` typing on the NIC map. No variable block change needed.

### Usage in tfvars (after module is updated)

```hcl
nic = {
  nic1 = {
    subnet                        = "MAZ"
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.x.x.x"
    ip_configuration_name         = "ipconfig1"  # only needed for migrated VMs
  }
}
```

### Backward compatibility

Fully backward compatible — `try()` falls back to the existing default when `ip_configuration_name` is absent. No change required for new VMs.
