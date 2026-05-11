# HCL Patterns — Verbatim Templates

Use when: implementing a specific block type during an ESLZ upgrade. Copy, adapt, and gate with `try()`.

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
