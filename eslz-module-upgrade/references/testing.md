# Terraform Test Patterns

Use when: creating or extending `tests/*.tftest.hcl` for an ESLZ module.

---

## File layout

```
<module-root>/
├── tests/
│   ├── <resource>.tftest.hcl          # functional tests (plan only)
│   └── upgrade_compat.tftest.hcl      # state-chaining upgrade safety test
```

## Skeleton — minimal working test file

```hcl
# tests/<resource>.tftest.hcl
mock_provider "azurerm" {}
mock_provider "null" {}

variables {
  resource_groups   = { rg-test = { name = "rg-test", location = "canadacentral" } }
  subnets           = {}
  env               = "Dev"
  userDefinedString = "test"
}

run "naming_convention" {
  command = plan
  variables {
    container_group = {
      resource_group = "rg-test"
      location       = "canadacentral"
      os_type        = "Linux"
      containers     = [{ name = "app", image = "nginx:latest", cpu = 0.5, memory = 0.5 }]
    }
  }
  assert {
    condition     = azurerm_container_group.container_group.name == "DevSLD-test-ci"
    error_message = "Name must follow {env}SLD-{userDefinedString}-ci convention"
  }
}
```

## Standard test cases

| Run name | What it tests |
|---|---|
| `naming_convention` | Name matches `{env}SLD-{userDefinedString}-ci` |
| `default_values` | Plan succeeds with minimal required inputs |
| `single_registry_credential` | Old single-object format still works |
| `multi_registry_credentials` | New list format works |
| `spot_priority_no_subnet` | `ip_address_type = "None"`, subnet omitted — no crash |
| `multi_port_container` | `ports = [{port=80,...},{port=443,...}]` in container |
| `no_dns_config` | Container group without dns_config — no crash |
| `with_diagnostics` | diagnostics block renders correctly |

## Assert patterns

```hcl
# String equality
assert { condition = azurerm_container_group.container_group.name == "DevSLD-test-ci", error_message = "..." }
# Attribute is null
assert { condition = azurerm_container_group.container_group.subnet_ids == null, error_message = "..." }
# Collection length
assert { condition = length(azurerm_container_group.container_group.container) == 1, error_message = "..." }
```

## Run-level variable override

```hcl
run "spot_priority_no_subnet" {
  command = plan
  variables {
    container_group = {
      resource_group = "rg-test", location = "canadacentral", os_type = "Linux"
      ip_address_type = "None", priority = "Spot"
      containers = [{ name = "app", image = "nginx:latest", cpu = 0.5, memory = 0.5 }]
    }
  }
  assert { condition = azurerm_container_group.container_group.subnet_ids == null, error_message = "subnet_ids must be null for Spot/None" }
}
```

## Notes

```
# mock_provider: intercepts all API calls — no Azure credentials needed
# CRITICAL: add sensitive = true to any output referencing full resource object
#   mock providers surface nested sensitive attrs (e.g. registry passwords) → test fails without it

# Running:
#   terraform init -backend=false    # must run before terraform test
#   terraform test                   # expected: "N passed, 0 failed"
```

## Upgrade compatibility test (`tests/upgrade_compat.tftest.hcl`)

```hcl
# Purpose: catch breaking resource changes before dev tests on real infra
# How: run blocks share state — apply creates mock state; next plan runs against it
# If upgraded code causes address change or accidental destroy → appears in plan
mock_provider "azurerm" {}
mock_provider "random" {}

variables { /* same shared variables as functional test */ }

# Step 1: simulate currently-deployed resource (pre-upgrade inputs)
run "baseline_apply" {
  command = apply
  variables { <resource> = { /* minimal pre-upgrade config — no new args */ } }
  assert { condition = <resource_type>.<resource_name>.name == "<expected_name>", error_message = "Baseline apply: unexpected resource name" }
}

# Step 2: plan upgraded code against that state
run "upgrade_plan_no_replacement" {
  command = plan    # plans against state from baseline_apply
  variables { <resource> = { /* same as baseline + new args added */ new_argument = true } }
  assert { condition = <resource_type>.<resource_name>.name == "<expected_name>", error_message = "Resource name must be unchanged after upgrade" }
  assert { condition = <resource_type>.<resource_name>.new_argument == true, error_message = "new_argument must be set" }
}
```

```
# What upgrade_compat catches vs misses:
CATCHES:  resource address changes (rename without moved block) → destroy+create in plan
CATCHES:  accidental resource removal → destroy in plan
CATCHES:  safe additive changes → shows ~ update in-place, 0 to destroy
MISSES:   ForceNew attribute changes — mock_provider ignores ForceNew; all changes appear in-place
          Verified empirically: changing location (ForceNew on azurerm_synapse_workspace) shows
          ~ update in-place, not destroy+create. Real provider would replace.

# ForceNew detection requires real terraform plan with credentials:
sh("terraform plan -out=upgrade.tfplan")
sh("""terraform show -json upgrade.tfplan | jq '
  [.resource_changes[] | select(.change.action_reason // "" | test("replace"))]
  | if length > 0 then error("unexpected replacements: \(.)") else "ok: no replacements" end'
""")
```

## Common test failures

| Error | Cause | Fix |
|---|---|---|
| `Output refers to sensitive values` | Output exposes full resource object | Add `sensitive = true` to output |
| `Invalid escape sequence` | `[^\/]` in regex | Change to `[^/]` |
| `true and false result expressions must have consistent types` | `can(tolist(x)) ? x : [x]` | Use `try(tolist(x), [x])` |
| `Invalid value for variable` | Required variable missing from test | Add to shared `variables {}` block |
| Provider not initialized | `terraform test` before `terraform init` | Run `terraform init -backend=false` first |
