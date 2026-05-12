---
agents:
    - copilot
categories:
    - software-development
description: |
    Scaffold a complete Terraform module for any Azure provider resource (azurerm or azuread) following the Shared Services Canada (SSC) Cloud Adoption Framework (CAF) naming and tagging standard. Use this skill whenever the user wants to create, scaffold, generate, or build a new Terraform CAF module for any Azure resource type — including when they provide a Terraform registry URL. Trigger on phrases like "create a CAF module for", "scaffold a terraform-azurerm-caf module", "build a CAF wrapper for", "create an ESLZ module for", even if the user just pastes a Terraform registry URL and says "make a module for this". The skill handles both azurerm (infrastructure) and azuread (Entra ID) resources. DO NOT trigger for general Terraform questions, editing existing modules, or non-Azure providers.
license: MIT
metadata:
    github-path: terraform-caf-azurerm-module
    github-ref: refs/tags/v1.0.0
    github-repo: https://github.com/bmaltais/skills
    github-tree-sha: 7fd979b07a06fd2c8a8f8d042bf0e0fcbd8ce76a
    scope: global
    source: custom
name: terraform-caf-azurerm-module
---
# Terraform CAF Module Scaffolder (SSC Standard)

You are scaffolding a Terraform module following the Shared Services Canada (SSC) Cloud
Adoption Framework (CAF) naming and tagging standard. Work through the steps below in order.
Write every file to disk using the Write tool — do not just show code in the chat.

---

## STEP 1 — Identify the target resource

Extract the Azure provider resource type from the user's request.

- If the user provided a **Terraform registry URL**, parse the resource name from the URL path
  (e.g., `.../resources/attestation_provider` → `azurerm_attestation_provider`)
- Determine whether it is an `azurerm` or `azuread` resource
- Note the full resource type (e.g., `azurerm_storage_account`, `azuread_application`)

---

## STEP 2 — Fetch registry documentation

The Terraform Registry UI requires JavaScript — WebFetch cannot render it. Always fetch raw
provider docs from GitHub:

- **azurerm**: `https://raw.githubusercontent.com/hashicorp/terraform-provider-azurerm/main/website/docs/r/<resource_name>.html.markdown`
- **azuread**: `https://raw.githubusercontent.com/hashicorp/terraform-provider-azuread/main/docs/resources/<resource_name>.md`

Where `<resource_name>` is the type with the provider prefix stripped
(e.g., `azurerm_storage_account` → `storage_account`, `azuread_application` → `application`).

Read the full doc. If it is very long, read it in sections. You need all arguments, blocks, and
their defaults before proceeding.

---

## STEP 3 — Analyze and plan

From the docs, classify every argument:

| Classification | Action in module |
|---|---|
| Required top-level | Direct assignment |
| Optional top-level | `try(var.<res>_config.<attr>, <registry_default>)` |
| Optional nested block (single) | `dynamic` block with `for_each = try(var.<res>_config.<block>, null) != null ? [1] : []` |
| Optional nested block (multi) | `for_each` over a map under the config object |
| Sensitive (password, key, cert) | Add to `lifecycle { ignore_changes = [...] }` |

Then decide:

**Device type** (azurerm only — 3-char SACM code, pick best fit):

| Code | Use for |
|---|---|
| SRV | Generic server/compute |
| SWx | Windows server (SWA=AD, SWB=DB, SWC=Web, SWJ=Jump) |
| SLx | Linux server functional subtypes |
| CNR | Cloud Network Resource (VNets, NICs, NSGs, LBs, gateways) |
| CSA | Cloud Storage Account |
| CSV | Cloud Secret Vault (Key Vault) |
| CCR | Cloud Container Registry |
| CPS | Cloud Platform Service (PaaS services without better match) |
| CLD | Generic cloud object |
| FWL | Firewall |
| ADC | Application Delivery Controller / Load Balancer |
| BST | Bastion Host |

**Resource suffix** (pick from SSC Table 4, or add following MS CAF convention):

`nic#`, `nsg`, `pip#`, `osdisk#`, `datadisk#`, `kv`, `stg`, `vnet`, `snet`, `rt`, `lb`,
`as`, `agw`, `fn`, `atp`, `law`, `fnc`, `bstn`, `azfw`, `sql`, `sdb`, `dsk`, `appi`…

> VMs have **no suffix**. Child objects always inherit parent name + suffix (e.g., `${local.vm-name}-nic1`).

**Supporting files** — include only if the resource warrants them:

- `secret.tf` — resource has admin passwords or credentials that belong in Key Vault
- `backup.tf` — compute resource that supports RSV backup enrollment
- `autoshutdown.tf` — compute resource that supports dev/test auto-shutdown

---

## STEP 4 — Determine the output directory

Ask the user where to create the module, OR use the current working directory if it looks like
a module repo (contains `.tf` files or a `ESLZ/` folder). Create the directory if needed.

---

## STEP 5 — Write all files

Write every file using the Write tool. Never skip a file without explaining why.

### `name.tf`

For **azurerm** resources:

```hcl
locals {
  <resource>_regex    = "/[//\"'\\[\\]:|<>+=;,?*@&]/"
  env_4               = substr(var.env, 0, 4)
  serverType_3        = substr(var.<resource>_config.serverType, 0, 3)
  userDefinedString_7 = substr(var.userDefinedString, 0, 7)
  <resource>-name     = replace("${local.env_4}${local.serverType_3}-${local.userDefinedString_7}", local.<resource>_regex, "")
}
```

For **azuread App Registrations / Enterprise Apps**:

```hcl
locals {
  # SSC standard for App Registrations: <dept acronym bilingual>-<userDefined-string>
  application_name = "SSC-SPC-${var.userDefinedString}"
}
```

For **azuread Groups / Managed Identities**:

```hcl
locals {
  # SSC Entra ID groups: <dept><env><region>_<GroupType>_<userDefined>
  # underscore is the field delimiter for Entra ID objects (not hyphen)
  group_name = "${var.env}_APP_${var.userDefinedString}"
}
```

> Name rules: strip `< > % & \ ? / " ' [ ] : | + = ; , ? * @ &` via regex replace.
> Windows VMs: 15-char max. Storage accounts: lowercase alphanumeric only, no hyphens.
> Key Vaults: 3-24 chars. Child objects inherit parent name + suffix.

---

### `variables.tf`

```hcl
variable "location" {
  description = "Azure location for the resource"
  type        = string
  default     = "canadacentral"
}

variable "tags" {
  description = "Tags that will be applied to every associated resource"
  type        = map(string)
  default     = {}
}

variable "env" {
  description = "(Required) 4-character GC governance prefix: <dept(2)><env(1)><region(1)> e.g. ScPc = SSC Production Azure Canada Central"
  type        = string
}

variable "group" {
  description = "(Required) Character string defining the group for the target subscription"
  type        = string
}

variable "project" {
  description = "(Required) Character string defining the project for the target subscription"
  type        = string
}

variable "userDefinedString" {
  description = "(Required) User defined portion of the resource name"
  type        = string
}

variable "resource_groups" {
  description = "(Required) Resource group object map"
  type        = any
  default     = {}
}

variable "<resource>_config" {
  description = "Object containing all <resource> configuration parameters"
  type        = any
  default     = {}
}
```

- Omit `location` and `resource_groups` for pure `azuread` resources (no Azure region/RG)
- Add `variable "subnets" { type = any }` only if the resource has NIC/subnet config

---

### `locals.tf`

```hcl
locals {
  # Accepts either a resource group name (key in var.resource_groups map)
  # or a full Azure resource ID — both are common in CAF deployments
  resource_group_name = strcontains(var.<resource>_config.resource_group, "/resourceGroups/")
    ? regex("[^\\/]+$", var.<resource>_config.resource_group)
    : var.resource_groups[var.<resource>_config.resource_group].name
}
```

Omit `resource_group_name` for pure `azuread` resources.

Add backward-compat locals for any deprecated parameters shown in the registry docs:

```hcl
  # Backward compatibility: prefer new_param, fall back to old_param
  effective_param = try(var.<resource>_config.new_param, null) != null
    ? var.<resource>_config.new_param
    : try(var.<resource>_config.old_param, <default>)
```

---

### `module.tf`

```hcl
resource "azurerm_<resource>" "<logical_name>" {
  name                = local.<resource>-name
  resource_group_name = local.resource_group_name
  location            = var.location

  # Required parameters
  <required_param> = var.<resource>_config.<required_param>

  # Optional parameters — always try() with the registry-documented default
  <optional_param> = try(var.<resource>_config.<optional_param>, <registry_default>)

  # Optional single-instance block
  dynamic "<block>" {
    for_each = try(var.<resource>_config.<block>, null) != null ? [1] : []
    content {
      required_field = var.<resource>_config.<block>.required_field
      optional_field = try(var.<resource>_config.<block>.optional_field, <default>)
    }
  }

  # Multi-instance child block (NICs, disks, rules, etc.)
  # ... use for_each over a map key in the config object

  tags = merge(var.tags, try(var.<resource>_config.tags, {}))

  lifecycle {
    ignore_changes = [<sensitive_or_stable_fields>]
  }
}
```

For multi-instance sub-resources (NICs, managed disks, NSG associations):

```hcl
resource "azurerm_<child>" "<child_logical>" {
  for_each            = try(var.<resource>_config.<child_map>, {})
  name                = "${local.<resource>-name}-<suffix>${local.<index>}"
  resource_group_name = local.resource_group_name
  location            = var.location
  ...
  tags = merge(var.tags, try(each.value.tags, {}))
}
```

Tag pattern for VMs with computer_name override:

```hcl
tags = merge(var.tags, try(var.<res>_config.tags, {}),
  [try(var.<res>_config.computer_name, null) != null
    ? { "OsHostname" = var.<res>_config.computer_name }
    : null]...)
```

---

### `output.tf`

```hcl
output "<resource>_object" {
  description = "Outputs the entire <resource> object"
  value       = azurerm_<resource>.<logical_name>
}

output "<resource>_id" {
  description = "Outputs the id of the <resource>"
  value       = azurerm_<resource>.<logical_name>.id
}

output "<resource>_name" {
  description = "Outputs the name of the <resource>"
  value       = azurerm_<resource>.<logical_name>.name
}
```

For `azuread` resources, adapt outputs to the resource's actual exported attributes
(e.g., `client_id`, `object_id`, `display_name`) instead of generic `id`/`name`.

---

### `ESLZ/<ResourcePascalCase>.tf`

```hcl
variable "<resource>s" {
  description = "Map of <resource> configurations. Each key becomes the userDefinedString."
  type        = any
  default     = {}
}

module "<resource>" {
  source   = "github.com/canada-ca-terraform-modules/terraform-azurerm-caf-<resource_slug>V2"
  for_each = var.<resource>s

  env               = var.env
  group             = var.group
  project           = var.project
  userDefinedString = each.key
  location          = var.location
  tags              = local.tags
  resource_groups   = local.resource_groups
  # subnets         = local.subnets  # uncomment if resource uses subnets

  <resource>_config = each.value
}
```

---

### `ESLZ/<ResourcePascalCase>.tfvars`

Realistic Canadian government infrastructure example. Set required fields, include ALL optional
fields/blocks as commented-out examples with inline descriptions:

```hcl
<resource>s = {
  example = {
    serverType     = "<SACM_code>"    # 3-char SACM device type
    resource_group = "Project"        # key in resource_groups map, or full Azure resource ID

    # Required resource-specific parameters
    <required_field> = "<realistic_value>"

    # Optional: Brief description of what this does
    # <optional_field> = "<example_value>"

    # Optional: Uncomment to configure <block_name> — brief description
    # <block_name> = {
    #   <field> = "<value>"    # inline description
    # }
  }
}
```

---

## STEP 6 — Conditional supporting files

### `secret.tf` (include when resource has admin passwords/credentials)

```hcl
locals {
  # KV name: derived from env, group, project, and SHA1 of KV resource group ID
  # to produce a deterministic, unique name that stays under the 24-char limit
  kv-name = substr(
    "${local.env_4}CSV-${var.group}_${var.project}-${substr(sha1(data.azurerm_resource_group.kv_rg.id), 0, 8)}-kv",
    0, 24
  )
}

data "azurerm_resource_group" "kv_rg" {
  name = try(var.<res>_config.key_vault.resource_group_name, var.resource_groups["Keyvault"].name)
}

data "azurerm_key_vault" "kv" {
  name                = try(var.<res>_config.key_vault.name, local.kv-name)
  resource_group_name = data.azurerm_resource_group.kv_rg.name
}

resource "random_password" "<res>-admin-password" {
  count   = try(var.<res>_config.admin_password, "") == "" ? 1 : 0
  length  = 20
  special = true
}

resource "azurerm_key_vault_secret" "<res>-admin-password" {
  count        = try(var.<res>_config.admin_password, "") == "" ? 1 : 0
  name         = local.<res>-name
  value        = random_password.<res>-admin-password[0].result
  key_vault_id = data.azurerm_key_vault.kv.id
}
```

### `backup.tf` (include for compute resources supporting RSV backup)

```hcl
locals {
  postfix      = "-rsv"
  rsv-name     = substr(replace("${local.env_4}CNR-${var.group}-${var.project}${local.postfix}", "/[^0-9A-Za-z-]/", ""), 0, 50)
  backup-policy-name = strcontains(try(var.<res>_config.backup_policy, "daily1"), "/resourceGroups/")
    ? regex("[^\\/]+$", var.<res>_config.backup_policy)
    : "${var.env}CNR-${var.group}_${var.project}-${try(var.<res>_config.backup_policy, "daily1")}-rsvp"
}

data "azurerm_recovery_services_vault" "rsv" {
  count               = try(var.<res>_config.disable_backup, false) ? 0 : 1
  name                = local.rsv-name
  resource_group_name = var.resource_groups["Backups"].name
}

data "azurerm_backup_policy_vm" "backup_policy" {
  count               = try(var.<res>_config.disable_backup, false) ? 0 : 1
  name                = local.backup-policy-name
  recovery_vault_name = data.azurerm_recovery_services_vault.rsv[0].name
  resource_group_name = data.azurerm_recovery_services_vault.rsv[0].resource_group_name
}

resource "azurerm_backup_protected_vm" "backup_vm" {
  count               = try(var.<res>_config.disable_backup, false) ? 0 : 1
  resource_group_name = data.azurerm_recovery_services_vault.rsv[0].resource_group_name
  recovery_vault_name = data.azurerm_recovery_services_vault.rsv[0].name
  source_vm_id        = azurerm_<resource>.<logical_name>.id
  backup_policy_id    = data.azurerm_backup_policy_vm.backup_policy[0].id

  lifecycle {
    ignore_changes       = [source_vm_id]
    replace_triggered_by = [azurerm_<resource>.<logical_name>.id]
  }
}
```

### `autoshutdown.tf` (include for compute resources)

```hcl
resource "azurerm_dev_test_global_vm_shutdown_schedule" "auto_shutdown" {
  count              = try(var.<res>_config.auto_shutdown_config, null) != null ? 1 : 0
  virtual_machine_id = azurerm_<resource>.<logical_name>.id
  location           = var.location
  enabled            = try(var.<res>_config.auto_shutdown_config.enabled, true)
  daily_recurrence_time = var.<res>_config.auto_shutdown_config.daily_recurrence_time
  timezone           = try(var.<res>_config.auto_shutdown_config.timezone, "Eastern Standard Time")

  notification_settings {
    enabled         = try(var.<res>_config.auto_shutdown_config.notification_settings.enabled, false)
    email           = try(var.<res>_config.auto_shutdown_config.notification_settings.email, "")
    time_in_minutes = try(var.<res>_config.auto_shutdown_config.notification_settings.time_in_minutes, 30)
  }
}
```

---

## STEP 7 — Run terraform fmt and validate

After writing all files, run:

```bash
terraform fmt -recursive
terraform validate
```

Fix any validation errors before presenting results to the user.

---

## STEP 8 — Generate agent instructions at module root (not ESLZ)

After terraform validates, generate instruction files at the **module root only**.

Never generate instruction files inside `ESLZ/`.

- Do NOT create `ESLZ/CLAUDE.md`
- Do NOT create `ESLZ/.github/copilot-instructions.md`
- Do NOT create any `.github/` folder under `ESLZ/`

### Copilot-only mode

If the user request includes `--copilot-only`:

- Create only: `.github/copilot-instructions.md`
- Do not create `CLAUDE.md`

### Default mode

If `--copilot-only` is not provided:

- Create `CLAUDE.md` at module root
- Create `.github/copilot-instructions.md` at module root

### `.github/copilot-instructions.md` format

Use full content (not a thin pointer) so Copilot can consume context directly. Start with:

```markdown
<!-- spectre: copilot-only -->
<!-- migrated from CLAUDE.md on YYYY-MM-DD -->
# Copilot Instructions
```

Then include the same practical sections used in this module family:

- Commands (`terraform init`, `terraform validate`, `terraform fmt -recursive`, `terraform plan/apply` using the generated ESLZ tfvars path)
- Architecture and naming convention
- Key design patterns detected in generated files
- File layout table for generated module files
- Agent Guidance checklist:
  1. Read `variables.tf`, then `locals.tf`, then target file
  2. Reference `ESLZ/` consumer before changing interfaces
  3. Check naming side-effects before changing `env/group/project/userDefinedString`
  4. Do not edit README between TF_DOCS markers
  5. Run `terraform fmt -recursive` after `.tf` edits

### `CLAUDE.md` format (default mode only)

Create the same content structure as `.github/copilot-instructions.md`, adapted for terminal-first usage.

---

## STEP 9 — Print summary

After all files are written and validated, print a table listing every file created:

| File | Purpose |
|---|---|
| `name.tf` | CAF name computation using env/serverType/userDefinedString locals |
| `variables.tf` | Standard CAF inputs + single `type=any` resource config object |
| `locals.tf` | Resource group resolution (name or ID), backward-compat locals |
| `module.tf` | Main resource + child resources with try() for all optional params |
| `output.tf` | Resource object, id, and name outputs |
| `ESLZ/<Resource>.tf` | Consumer for_each module call |
| `ESLZ/<Resource>.tfvars` | Fully-commented example values |
| _(if included)_ `secret.tf` | Key Vault password management |
| _(if included)_ `backup.tf` | RSV backup enrollment |
| _(if included)_ `autoshutdown.tf` | Dev/test auto-shutdown schedule |

---

## SSC CAF Quick Reference

### Name structure

```
<dept(2)><env(1)><region(1)><deviceType(3)>-<userDefined>[-<suffix>]
```

Example: `ScPcSWA-myapp01` (SSC, Production, Azure Central, Server Windows AD, user string "myapp01")

### var.env values

The 4-char prefix encodes: `<dept><env><region>`
- Sc = SSC, P = Production, c = Azure Canada Central → `ScPc`
- Sc = SSC, D = Development, d = Azure Canada East → `ScDd`

### Entra ID naming

Groups use underscore `_` as field delimiter (not hyphen):
`<dept><env><region>_<GroupType>_<UserDefined>`

App Registrations use bilingual dept acronym:
`SSC-SPC-<UserDefined>`

### Mandatory governance tags (always passed via var.tags by the caller)

| Key | Example value |
|---|---|
| `costcenter` | `22578-proj_123` |
| `env` | `dev` |
| `classification` | `pbmm` |
| `owner` | `jane.doe@canada.ca` |

Always merge: `tags = merge(var.tags, try(var.<res>_config.tags, {}))`
