# Implementation Patterns Reference

## Count / for_each guard

After adding a conditional `count` or `for_each` on a module, grep every repo
reference and wrap any external access in `try()`:

```bash
grep -rn 'module\.<name>\["<key>"\]' .
```

```hcl
# WRONG — errors when key is absent from for_each
object_id = module.app_registrationsV2["devops"].aad_sp_object.object_id

# CORRECT
object_id = try(module.app_registrationsV2["devops"].aad_sp_object.object_id, null)
```

Do not proceed to Step 4 until all callers are guarded.

## Backward compatibility rules

- Never remove or rename existing arguments.
- Never change a `count`/`for_each` expression unless the user explicitly asks.
- For new optional arguments: use `try(var.x, <provider_default>)` so existing
  callers that don't pass the argument get the provider default unchanged.
- For `triggers` blocks: add alongside existing `depends_on` — do not replace it.

## Adding `triggers` for re-sync (common pattern)

```hcl
resource "azurerm_virtual_network_peering" "example" {
  # ... existing arguments unchanged ...

  triggers = {
    remote_address_space = join(",", data.azurerm_virtual_network.remote[0].address_space)
  }

  depends_on = [existing_dependency]   # kept as-is
}
```

## Naming decision rule

When adding a **new** interface/resource for a feature's first implementation,
use neutral names (e.g. `managed_identities`) — no version suffix. Use versioned
names only when an existing V1 implementation must coexist for state-migration safety.

## azuread deprecation: end_date_relative

`end_date_relative` is deprecated. Use `end_date` + `lifecycle`:

```hcl
end_date = timeadd(timestamp(), "8760h")

lifecycle {
  ignore_changes = [end_date]   # mandatory — timestamp() advances every plan
}
```
