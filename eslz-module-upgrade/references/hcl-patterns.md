# HCL Patterns — Verbatim Templates

Use when: implementing a specific block type during an ESLZ upgrade. Copy, adapt, and gate with `try()`.

---

## SSC name.tf pattern — standard naming formula for every new module

Use for every new module and every upgrade. The formula follows SSC Azure Naming Standard v2.1:
`{env4}{serverType3}-{userDefinedString}` where `env` = `<dept(2)><env(1)><region(1)>` (4 chars total).

### Device type quick-reference (most common)

| Code | Use for |
|---|---|
| `CPS` | Cloud Platform Service — generic PaaS (Redis, Service Bus, Event Hub, etc.) |
| `CNR` | Cloud Network Resource — VNets, NICs, NSGs, route tables, gateways |
| `CSV` | Cloud Secret Vault — Key Vault |
| `CSA` | Cloud Storage Account |
| `SWA`–`SWJ` | Windows server functions (A=AD/DNS, B=DB, C=Web, D=App, E=Mgmt, F=File, G=Cluster, H=Messaging, J=Jump) |
| `SLA`–`SLC` | Linux server functions (A=AD/DNS, B=DB, C=Web) |
| `SRV` | Generic server (no specific OS/function) |

For a full table run the `ssc-azure-naming` skill.

### name.tf — standard single-resource module

```hcl
locals {
  # Strip characters invalid in Azure resource names (adjust regex per resource type)
  # Managed Redis / most PaaS: alphanumeric and hyphens only
  <resource>_regex         = "/[^a-zA-Z0-9-]/"
  env_4                    = substr(var.env, 0, 4)
  serverType_3             = substr(var.serverType, 0, 3)
  userDefinedString_7      = substr(var.userDefinedString, 0, 7)

  # SSC formula: {dept(2)}{env(1)}{region(1)}{deviceType(3)}-{userDefined}
  # Example: ScPcCPS-myapp (SSC Production Canada Central, Cloud Platform Service)
  # Override with var.<resource>.<resource>_name to pin to an existing deployment name.
  <resource>-name = try(
    trimspace(var.<resource>.<resource>_name) != "" ? trimspace(var.<resource>.<resource>_name) : replace("${local.env_4}${local.serverType_3}-${local.userDefinedString_7}", local.<resource>_regex, ""),
    replace("${local.env_4}${local.serverType_3}-${local.userDefinedString_7}", local.<resource>_regex, "")
  )
}
```

### variables.tf — required naming variables with SSC-compliant descriptions

```hcl
variable "env" {
  description = "(Required) 4-character SSC naming prefix composed of dept(2)+env(1)+region(1), e.g. ScPc = SSC Production Canada Central, ScDc = SSC Development Canada Central. See SSC Azure Naming Standard v2.1."
  type        = string
}

variable "userDefinedString" {
  description = "(Required) User-defined portion of the resource name following the SSC naming convention. May include hyphens for sub-field separation."
  type        = string
}

variable "serverType" {
  description = "3-character SSC SACM device type appended directly to the env prefix before the hyphen. Defaults to <CODE> (<description>). Override with a more specific code if needed. See SSC Azure Naming Standard v2.1 device type table."
  type        = string
  default     = "<CODE>"  # e.g. CPS for generic PaaS, CNR for networking
}
```

### Per-instance naming in `locals.tf` (fleet/map modules)

When a module manages N instances keyed by a map, compute names in the enriched map rather than in `name.tf`:

```hcl
locals {
  base-name = replace("${local.env_4}${local.serverType_3}-${local.userDefinedString_7}", local.<resource>_regex, "")

  instances = {
    for ik, inst in try(var.<resource>.instances, {}) :
    ik => merge(inst, {
      # Auto-name: {base-name}-{instance_key}; override with instance.<resource>_name
      _name = try(
        trimspace(inst.<resource>_name) != "" ? trimspace(inst.<resource>_name) : "${local.base-name}-${ik}",
        "${local.base-name}-${ik}"
      )
    })
  }
}
```

---

## N:M flatten pattern — nested resources with composite keys

Use when a module manages N parent resources (e.g. capacity pools) each containing M child resources (e.g. volumes). Avoids separate `for_each` variables per level.

### Rule: key delimiter
Use `--` as the composite key delimiter. Azure resource names cannot contain `--`, so it is safe as a separator at all hierarchy levels (e.g. `pool_key--vol_key--rule_key`).

### locals.tf — enriched parent map + flat child map

```hcl
locals {
  # Parents — enriched with computed name
  # Override with parent.parent_name; auto-generate as {base-name}-{parent_key}
  parents = {
    for pk, p in try(var.module_input.parents, {}) :
    pk => merge(p, {
      _name = try(trimspace(p.parent_name) != "" ? trimspace(p.parent_name) : "${local.base-name}-${pk}", "${local.base-name}-${pk}")
    })
  }

  # Children flat map — key: "{parent_key}--{child_key}"
  # Override with child.child_name; auto-generate as {base-name}-{child_key}
  children_flat = {
    for item in flatten([
      for pk, p in try(var.module_input.parents, {}) : [
        for ck, c in try(p.children, {}) : {
          key        = "${pk}--${ck}"
          parent_key = pk
          name       = try(trimspace(c.child_name) != "" ? trimspace(c.child_name) : "${local.base-name}-${ck}", "${local.base-name}-${ck}")
          config     = c
        }
      ]
    ]) : item.key => merge(item.config, {
      _parent_key = item.parent_key
      _name       = item.name
    })
  }

  # Grandchildren flat map — key: "{parent_key}--{child_key}--{grandchild_key}"
  grandchildren_flat = {
    for item in flatten([
      for pk, p in try(var.module_input.parents, {}) : [
        for ck, c in try(p.children, {}) : [
          for gk, g in try(c.grandchildren, {}) : {
            key            = "${pk}--${ck}--${gk}"
            child_flat_key = "${pk}--${ck}"
            name           = try(trimspace(g.rule_name) != "" ? trimspace(g.rule_name) : "${local.base-name}-${gk}", "${local.base-name}-${gk}")
            config         = g
          }
        ]
      ]
    ]) : item.key => merge(item.config, {
      _child_flat_key = item.child_flat_key
      _name           = item.name
    })
  }
}
```

### module.tf — resources referencing each other by flat key

```hcl
resource "azurerm_<parent>" "parents" {
  for_each = local.parents
  name     = each.value._name
  # ... other args
}

resource "azurerm_<child>" "children" {
  for_each    = local.children_flat
  name        = each.value._name
  parent_name = azurerm_<parent>.parents[each.value._parent_key].name
  # ... other args
}

resource "azurerm_<grandchild>" "grandchildren" {
  for_each   = local.grandchildren_flat
  name       = each.value._name
  child_id   = azurerm_<child>.children[each.value._child_flat_key].id
  # ... other args
}
```

### tests — assert counts and composite key names

```hcl
run "multi_parent_multi_child" {
  command = plan

  variables {
    module_input = {
      parents = {
        p1 = {
          # ...
          children = {
            c1 = { /* ... */ }
            c2 = { /* ... */ }
          }
        }
        p2 = {
          children = {
            c1 = { /* ... */ }
          }
        }
      }
    }
  }

  assert {
    condition     = length(azurerm_<parent>.parents) == 2
    error_message = "Two parent resources must be created"
  }

  assert {
    condition     = length(azurerm_<child>.children) == 3
    error_message = "Three child resources must be created across both parents"
  }

  assert {
    condition     = azurerm_<child>.children["p1--c1"].name == "DevXXX-test-c1"
    error_message = "Child name must follow {base-name}-{child_key}"
  }
}
```

### name.tf — scalar names only; per-instance names stay in locals.tf

`name.tf` must only contain names that apply to the entire module call (e.g. account name, backup vault name). Per-instance names (pool names, volume names, policy names) must be computed as `_name` attributes inside the enriched map in `locals.tf`. Mixing per-instance names into `name.tf` produces stale locals when the resource set changes.

```hcl
# name.tf — scalar names only
locals {
  account-name      = try(trimspace(var.module_input.account_name) != "" ? trimspace(var.module_input.account_name) : local.base-name, local.base-name)
  backup-vault-name = try(trimspace(var.module_input.backup_vault.vault_name) != "" ? trimspace(var.module_input.backup_vault.vault_name) : "${local.base-name}-bkpvlt", "${local.base-name}-bkpvlt")
  # DO NOT put per-instance names (pool/volume/policy names) here
}
```

---

## init_container block

```hcl
dynamic "init_container" {
  for_each = try(var.container_group.init_containers, [])
  content {
    name                         = init_container.value["name"]
    image                        = init_container.value["image"]
    environment_variables        = try(init_container.value["environment_variables"], {})
    secure_environment_variables = try(init_container.value["secure_environment_variables"], {})
    commands                     = try(init_container.value["commands"], [])

    dynamic "volume" {
      for_each = try(init_container.value["volumes"], [])
      content {
        name                 = volume.value["name"]
        mount_path           = volume.value["mount_path"]
        read_only            = try(volume.value["read_only"], false)
        empty_dir            = try(volume.value["empty_dir"], false)
        storage_account_name = try(volume.value["storage_account_name"], null)
        storage_account_key  = try(volume.value["storage_account_key"], null)
        share_name           = try(volume.value["share_name"], null)
        secret               = try(volume.value["secret"], null)
        dynamic "git_repo" {
          for_each = try(volume.value["git_repo"], null) != null ? [1] : []
          content {
            url       = volume.value["git_repo"]["url"]
            directory = try(volume.value["git_repo"]["directory"], null)
            revision  = try(volume.value["git_repo"]["revision"], null)
          }
        }
      }
    }

    dynamic "security" {
      for_each = try(init_container.value["security"], null) != null ? [1] : []
      content {
        privilege_escalation_allowed = try(init_container.value["security"]["privilege_escalation_allowed"], false)
      }
    }
  }
}
```

## diagnostics block (log_analytics)

```hcl
dynamic "diagnostics" {
  for_each = try(var.container_group.diagnostics, null) != null ? [1] : []
  content {
    log_analytics {
      workspace_id  = var.container_group.diagnostics["workspace_id"]
      workspace_key = var.container_group.diagnostics["workspace_key"]
      log_type      = try(var.container_group.diagnostics["log_type"], null)
      metadata      = try(var.container_group.diagnostics["metadata"], null)
    }
  }
}
```

## exposed_port block (group-level, distinct from container ports)

```hcl
dynamic "exposed_port" {
  for_each = try(var.container_group.exposed_ports, [])
  content {
    port     = exposed_port.value["port"]
    protocol = try(exposed_port.value["protocol"], "TCP")
  }
}
```

## identity block

```hcl
dynamic "identity" {
  for_each = try(var.container_group.identity, null) != null ? [1] : []
  content {
    type         = var.container_group.identity["type"]
    identity_ids = try(var.container_group.identity["identity_ids"], [])
  }
}
```

## volume block (inside container)

```hcl
dynamic "volume" {
  for_each = try(container.value["volumes"], [])
  content {
    name                 = volume.value["name"]
    mount_path           = volume.value["mount_path"]
    read_only            = try(volume.value["read_only"], false)
    empty_dir            = try(volume.value["empty_dir"], false)
    storage_account_name = try(volume.value["storage_account_name"], null)
    storage_account_key  = try(volume.value["storage_account_key"], null)
    share_name           = try(volume.value["share_name"], null)
    secret               = try(volume.value["secret"], null)
    dynamic "git_repo" {
      for_each = try(volume.value["git_repo"], null) != null ? [1] : []
      content {
        url       = volume.value["git_repo"]["url"]
        directory = try(volume.value["git_repo"]["directory"], null)
        revision  = try(volume.value["git_repo"]["revision"], null)
      }
    }
  }
}
```

## readiness_probe / liveness_probe blocks (inside container)

Both probes share the same structure — swap `readiness_probe` for `liveness_probe` as needed:

```hcl
dynamic "readiness_probe" {
  for_each = try(container.value["readiness_probe"], null) != null ? [1] : []
  content {
    exec                  = try(container.value["readiness_probe"]["exec"], null)
    initial_delay_seconds = try(container.value["readiness_probe"]["initial_delay_seconds"], null)
    period_seconds        = try(container.value["readiness_probe"]["period_seconds"], 10)
    failure_threshold     = try(container.value["readiness_probe"]["failure_threshold"], 3)
    success_threshold     = try(container.value["readiness_probe"]["success_threshold"], 1)
    timeout_seconds       = try(container.value["readiness_probe"]["timeout_seconds"], 1)

    dynamic "http_get" {
      for_each = try(container.value["readiness_probe"]["http_get"], null) != null ? [1] : []
      content {
        path   = try(container.value["readiness_probe"]["http_get"]["path"], "/")
        port   = container.value["readiness_probe"]["http_get"]["port"]
        scheme = try(container.value["readiness_probe"]["http_get"]["scheme"], "Http")
        http_headers = try(container.value["readiness_probe"]["http_get"]["http_headers"], null)
      }
    }
  }
}
```

## security block (inside container — privilege escalation)

```hcl
dynamic "security" {
  for_each = try(container.value["security"], null) != null ? [1] : []
  content {
    privilege_escalation_allowed = try(container.value["security"]["privilege_escalation_allowed"], false)
  }
}
```

## image_registry_credential — normalized single-or-list

Always normalize in locals.tf first:

```hcl
# locals.tf
_image_registry_credentials_raw = try(var.container_group.image_registry_credentials, [])
image_registry_credentials = try(
  tolist(local._image_registry_credentials_raw),
  [local._image_registry_credentials_raw]
)
```

Then in module.tf:

```hcl
dynamic "image_registry_credential" {
  for_each = local.image_registry_credentials
  content {
    server                    = image_registry_credential.value["server"]
    username                  = try(image_registry_credential.value["username"], null)
    password                  = try(image_registry_credential.value["password"], null)
    user_assigned_identity_id = try(image_registry_credential.value["user_assigned_identity_id"], null)
  }
}
```

## dns_config — optional dynamic block

```hcl
dynamic "dns_config" {
  for_each = try(var.container_group.dns_config, null) != null ? [1] : []
  content {
    nameservers    = var.container_group.dns_config["nameservers"]
    search_domains = try(var.container_group.dns_config["search_domains"], null)
    options        = try(var.container_group.dns_config["options"], null)
  }
}
```

## ports — backward compat (singular port/protocol keys + new list)

```hcl
dynamic "ports" {
  for_each = try(
    container.value["ports"],
    try(container.value["port"], null) != null
      ? [{ port = container.value["port"], protocol = try(container.value["protocol"], "TCP") }]
      : []
  )
  content {
    port     = ports.value["port"]
    protocol = try(ports.value["protocol"], "TCP")
  }
}
```
