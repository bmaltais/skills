# Ecosystem — Companion Skills

Use when: deciding which skill to invoke alongside the upgrade, or when a gap is outside this skill's scope.

---

## Skill: spectre

**When to use alongside eslz-module-upgrade:**
- After the upgrade is complete — run `/spectre` to record a journal entry and capture lessons learned
- If a non-obvious pattern was discovered (new provider bug, new backward-compat technique), tell Spectre so it can persist the finding

**How to trigger:** `/spectre` at session end

---

## Provider documentation URLs

Always fetch raw GitHub markdown — Terraform registry pages require JavaScript and cannot be fetched with WebFetch:

```
https://raw.githubusercontent.com/hashicorp/terraform-provider-azurerm/refs/heads/main/website/docs/r/<resource>.html.markdown
```

Replace `<resource>` with the snake_case resource name (e.g. `container_group`, `kubernetes_cluster`, `storage_account`).

For a specific provider tag/version instead of `main`:
```
https://raw.githubusercontent.com/hashicorp/terraform-provider-azurerm/v4.50.0/website/docs/r/<resource>.html.markdown
```

---

## Terraform version requirements

| Feature | Min version |
|---|---|
| `terraform test` | 1.6 (experimental), GA in 1.7 |
| `mock_provider` | 1.7 |
| `moved` blocks | 1.1 |
| `try()` function | 0.13 |
| `strcontains()` function | 1.5 |

Recommend pinning CI to `~>1.9` to pick up all features.

---

## AzureRM provider compatibility notes

| Provider series | Notes |
|---|---|
| < 3.x | `azurerm_container_group` uses `ip_address {}` block — very different schema |
| 3.x | Transition period; some arguments renamed |
| >= 4.0 | Breaking changes: removed deprecated args; `subnet_ids` at top level not inside `ip_address {}` |
| 4.50 | Current stable; add `exposed_port`, `init_container`, `diagnostics` |

**Always check provider changelog** when the target version has a major number bump — breaking changes are common.

---

## Common pattern: `variable "X" { type = any }`

ESLZ modules use `type = any` for the main resource variable to avoid maintaining a rigid object schema. This enables callers to pass arbitrary keys that get accessed via `try()` in the module. The trade-off is that typos in keys are silent (no validation error). This is an accepted ESLZ convention — do not "fix" it by adding strict types unless the user explicitly asks.
