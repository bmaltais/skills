---
name: terraform-module-change
description: >
  End-to-end workflow for making a change to an existing Terraform module resource:
  fetch provider docs, implement the change, write a pure-logic tftest fixture (no
  provider credentials needed), wire test discovery via Makefile, run the full
  validation cycle (terraform test → fmt → tflint), and update RELEASE_NOTES.md.
  Use when the user asks to add, update, or fix an argument on an existing Terraform
  resource, add a new behaviour to an existing resource block, ensure a resource
  re-syncs on upstream changes, or "update X to use the new Y argument". Trigger on
  phrases like "update this resource to use", "add X to my terraform resource",
  "ensure sync when", "how do I make terraform detect changes in", "update my tf
  code for provider version X", "write tests for this tf change".
  DO NOT use for: scaffolding new modules (use terraform-caf-azurerm-module),
  full provider version upgrades across a module (use eslz-module-upgrade),
  or pure validation runs without code changes (use terraform-validation-workflow).
categories: [software-development]
agents: [copilot]
version: 1.0.0
metadata:
  source: custom
  scope: global
---

# Terraform Module Change Workflow

End-to-end workflow for implementing a targeted change to an existing Terraform
resource, with tests, validation, and release notes. Works for any azurerm /
azuread / azapi resource in any L1 or L2 blueprint.

---

## Step 1 — Read the current code

Read the target `.tf` file **before** making any changes.

- Identify the resource block(s) to change.
- Note all existing arguments, `count`/`for_each` expressions, `depends_on`, and
  `lifecycle` blocks — these must be preserved exactly.

---

## Step 2 — Fetch provider documentation

Fetch the resource docs for the **exact provider version** in use.

```bash
# Find the version constraint
grep -A5 'required_providers' main.tf | grep 'version'
```

Fetch docs from the Terraform Registry:
```
https://registry.terraform.io/providers/hashicorp/azurerm/<VERSION>/docs/resources/<resource_name>
```

Read the **Arguments Reference** section carefully. Note:
- New optional arguments and their defaults
- Arguments that use `triggers` or lifecycle hooks
- Any `Changing this forces a new resource` warnings (these are breaking if used)

---

## Step 3 — Implement the change

Edit only the target resource block(s). Do not touch unrelated code.

**When the change introduces a `count` or conditional `for_each` on a module:**

After implementing the guard, grep the entire repo for every reference to that
module key and verify each one is safe when the key is absent:

```bash
grep -rn 'module\.<name>\["<key>"\]' .
```

Every reference outside the module itself **must** be wrapped in `try()`:
```hcl
# WRONG — will error when "devops" key is absent from for_each
object_id = module.app_registrationsV2["devops"].aad_sp_object.object_id

# CORRECT
object_id = try(module.app_registrationsV2["devops"].aad_sp_object.object_id, null)
```

Do not proceed to Step 4 until all callers are guarded.

**Backward compatibility rules:**
- Never remove or rename existing arguments.
- Never change a `count`/`for_each` expression unless the user explicitly asks.
- For new optional arguments: use `try(var.x, <provider_default>)` so existing
  callers that don't pass the argument get the provider default unchanged.
- For `triggers` blocks (re-sync on upstream change): add them alongside existing
  `depends_on` — they do not replace it.

**Common pattern — adding `triggers` for re-sync:**
```hcl
resource "azurerm_virtual_network_peering" "example" {
  # ... existing arguments unchanged ...

  triggers = {
    remote_address_space = join(",", data.azurerm_virtual_network.remote[0].address_space)
  }

  depends_on = [existing_dependency]   # kept as-is
}
```

---

## Step 4 — Write a pure-logic test fixture

Create a self-contained test fixture that exercises the changed logic **without
requiring provider credentials**. Mirror only the locals/expressions that changed.

### Fixture location

```
tests/fixtures/<feature_name>/
  main.tf                          # pure locals + outputs, no providers
  <feature_name>.tftest.hcl        # plan-time assertions
```

### main.tf template

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
  # Mirror the expression from the production .tf file verbatim.
  # Add a comment pointing to the source file and line.
  #
  # Mirror of remote_vnet_peering.tf triggers block:
  computed_trigger = {
    key = join(",", var.remote_value)
  }

  resource_count = var.feature_enabled ? 1 : 0
}

output "resource_count"   { value = local.resource_count }
output "computed_trigger" { value = local.computed_trigger }
```

**Rules for the fixture `main.tf`:**
- Include `terraform { required_version = ">= 1.2.6" }`.
- No `provider` blocks, no `resource` blocks — only `variable`, `locals`, `output`.
- Each `local` must include a comment naming the source file it mirrors.
- Keep it minimal: only the logic under test, nothing else.
- Write output declarations in **fmt-canonical format** (no extra alignment spaces): `output "foo" { value = local.foo }`. `terraform fmt` collapses aligned spacing; pre-fmt content as `oldString` will fail to match if you edit the fixture again later.

### .tftest.hcl template

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

**Minimum test set per change:**
1. Feature disabled → `count == 0` (backward compat)
2. Feature enabled → `count == 1` (happy path)
3. New argument / expression produces expected value
4. Edge case (empty list, single item, long list, etc.)

---

## Step 5 — Wire test discovery

If a `tests/Makefile` does not exist, create it. If it already exists, verify the
new fixture is auto-discovered (no edit needed if using the glob pattern below).

```makefile
.PHONY: test

TEST_DIRS := $(sort $(dir $(wildcard fixtures/*/main.tf)))

## test: Run all terraform test suites under tests/fixtures/
test:
	@echo "==> Running all test suites..."
	@failed=0; \
	for dir in $(TEST_DIRS); do \
	  echo ""; \
	  echo "==> terraform test: $$dir"; \
	  (cd $$dir && terraform init -backend=false -input=false -no-color 2>&1 && terraform test -no-color) || failed=1; \
	done; \
	echo ""; \
	if [ $$failed -eq 0 ]; then \
	  echo "==> All tests passed."; \
	else \
	  echo "==> One or more test suites FAILED."; \
	  exit 1; \
	fi
```

The glob `fixtures/*/main.tf` auto-discovers new suites — no Makefile edits needed
when adding future fixtures.

---

## Step 6 — Run the full validation cycle

Run in this exact order. Stop on first failure.

```bash
# 1. Run all tests (from tests/ directory)
cd tests && make test

# 2. Format
cd ..   # back to module root
terraform fmt -recursive

# 3. Lint
tflint --recursive
```

> **Guard — editing fixture files after fmt:** `terraform fmt` rewrites whitespace
> in output and argument blocks. If you need to make further edits to any fixture
> file after running fmt, **re-read it first** — use the post-fmt content as
> `oldString`, not the content you originally wrote.

**Handling tflint warnings:**
- Fix warnings introduced by **your changes** immediately.
- For pre-existing warnings (present before your change), report them to the user
  but do not modify unrelated code.
- Never add `// nolint` or `.tflint.hcl` ignore rules to silence new warnings
  without the user's approval.

---

## Step 7 — Update RELEASE_NOTES.md

If a `RELEASE_NOTES.md` exists at the module root, prepend a new entry. Use today's
date in `YYYYMMDD.N` format (increment `.N` if multiple releases on the same day).

```markdown
## 20260525.0

- Brief description of what changed and why (one line per logical change).
- Add `triggers` to `azurerm_virtual_network_peering` resources so peering re-syncs when address space changes.
- Add `tests/fixtures/vnet_peering_triggers/` with 6 plan-time tests.
- Add `tests/Makefile` with auto-discovering `test` target.
```

**Rules:**
- Newest entry at the top.
- One bullet per logical change (not per file edited).
- Mention the affected `.tf` file or resource type so readers can find the change.
- Do not mention internal refactors, fmt, or tflint fixes unless the user asks.

---

## Checklist

Before declaring the work done, confirm every item:

- [ ] Provider docs read for the exact version in use
- [ ] Existing arguments and `depends_on` preserved unchanged
- [ ] New argument uses `try()` or a safe default for backward compat
- [ ] Test fixture has `terraform { required_version = ... }`
- [ ] Test fixture has no provider blocks (pure logic only)
- [ ] Tests cover: disabled (count=0), enabled (count=1), new behaviour, edge case
- [ ] `make test` passes from `tests/`
- [ ] `terraform fmt -recursive` produces no diff
- [ ] `tflint --recursive` introduces no new warnings vs. before the change
- [ ] RELEASE_NOTES.md updated with entry at the top
