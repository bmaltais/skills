# Test Fixture Templates

## Fixture layout

```
tests/fixtures/<feature_name>/
  main.tf                          # pure locals + outputs, no providers
  <feature_name>.tftest.hcl        # plan-time assertions
```

---

## main.tf template

```hcl
terraform {
  required_version = ">= 1.2.6"
}

# Variables that represent the inputs to the logic under test
variable "feature_enabled" {
  type    = bool
  default = false
}

variable "remote_value" {
  type    = list(string)
  default = []
}

locals {
  # Mirror of <source_file>.tf — <describe the expression>
  computed_trigger = {
    key = join(",", var.remote_value)
  }

  resource_count = var.feature_enabled ? 1 : 0
}

output "resource_count" { value = local.resource_count }
output "computed_trigger" { value = local.computed_trigger }
```

**Rules:**
- Include `terraform { required_version = ">= 1.2.6" }`.
- No `provider` blocks, no `resource` blocks — only `variable`, `locals`, `output`.
- Each `local` must include a comment naming the source file it mirrors.
- Keep it minimal: only the logic under test.
- Write output declarations in **fmt-canonical format** (no extra alignment spaces).
  `terraform fmt` collapses aligned spacing; always re-read after fmt before editing again.

---

## .tftest.hcl template

```hcl
# Tests for <feature> logic.
# Run from this directory: terraform test
# No real Azure credentials required — pure plan-time logic.

# ── Backward compatibility ───────────────────────────────────
run "feature_disabled_no_resources" {
  command = plan

  variables { feature_enabled = false }

  assert {
    condition     = output.resource_count == 0
    error_message = "Expected 0 resources when disabled, got ${output.resource_count}."
  }
}

# ── Happy path ───────────────────────────────────────────────
run "feature_enabled_creates_resource" {
  command = plan

  variables {
    feature_enabled = true
    remote_value    = ["10.0.0.0/16"]
  }

  assert {
    condition     = output.resource_count == 1
    error_message = "Expected 1 resource when enabled, got ${output.resource_count}."
  }
}

# ── New behaviour ────────────────────────────────────────────
run "trigger_tracks_remote_value" {
  command = plan

  variables {
    feature_enabled = true
    remote_value    = ["10.0.0.0/16", "10.1.0.0/16"]
  }

  assert {
    condition     = output.computed_trigger.key == "10.0.0.0/16,10.1.0.0/16"
    error_message = "trigger.key must join values, got: ${output.computed_trigger.key}."
  }
}

# ── Edge case ────────────────────────────────────────────────
run "single_value_no_trailing_delimiter" {
  command = plan

  variables {
    feature_enabled = true
    remote_value    = ["10.10.0.0/16"]
  }

  assert {
    condition     = output.computed_trigger.key == "10.10.0.0/16"
    error_message = "Single value must not have trailing delimiter, got: ${output.computed_trigger.key}."
  }
}
```

---

## Minimum test set per change

1. Feature disabled → `count == 0` (backward compat)
2. Feature enabled → `count == 1` (happy path)
3. New argument / expression produces expected value
4. Edge case (empty list, single item, long list, etc.)
