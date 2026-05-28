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

**Reference files** (load as needed):
- [ref-implementation-patterns.md](ref-implementation-patterns.md) — count/for_each guards, triggers, naming rules, deprecations
- [ref-test-fixture-templates.md](ref-test-fixture-templates.md) — main.tf and .tftest.hcl templates
- [ref-makefile-template.md](ref-makefile-template.md) — tests/Makefile template
- [ref-eslz-template.md](ref-eslz-template.md) — ESLZ tfvars example template
- [ref-ado-workflow.md](ref-ado-workflow.md) — ADO plan + completion comment scripts

---

## Step 1 — Read the current code

Read the target `.tf` file **before** making any changes. Note all existing
arguments, `count`/`for_each` expressions, `depends_on`, and `lifecycle` blocks —
these must be preserved exactly.

**When your plan introduces a NEW `variable` + `module` or `variable` + `resource`
block**, scan for related existing patterns first:

```bash
grep -rn 'source.*<module_fragment>' *.tf
grep -rn 'for_each.*var\.' *.tf
```

If a semantically related `variable + module/resource` already exists, **present
the extend-vs-add tradeoff to the user and wait for a choice before writing code**:

| | Extend existing variable | Add new variable |
|---|---|---|
| Pros | One variable to learn; no new module call | Clean separation; independent defaults |
| Cons | Callers must know new optional fields | Duplication if underlying resource is identical |

- **Add new** when: different defaults or lifecycle rules that would silently break existing entries.
- **Extend existing** when: purely opt-in behaviour, identical underlying resource, variable is `type = any`.

**Directory convention check:** before referencing a subdirectory (`ESLZ/`,
`tests/fixtures/`, `modules/`), verify it exists:

```bash
ls -1d */ 2>/dev/null
```

If it doesn't exist and you intend to create it, state that explicitly in the plan.

---

## Step 2 — Fetch provider documentation

```bash
grep -A5 'required_providers' main.tf | grep 'version'
```

Fetch docs:
```
https://registry.terraform.io/providers/hashicorp/azurerm/<VERSION>/docs/resources/<resource_name>
```

Read **Arguments Reference**. Note: new optional arguments, `triggers`/lifecycle
hooks, and `Changing this forces a new resource` warnings (breaking changes).

**Compatibility guard:** when the user targets a specific provider version that
differs from the pinned version, fetch docs for **both** and implement only the
required intersection. State explicitly which options are available in the target.

---

## Step 2b — Post plan to ADO work item (mandatory when a WI ID is in context)

Before writing any code, set WI to **Active** and post the implementation plan.
See [ref-ado-workflow.md](ref-ado-workflow.md) for exact commands.

Plan comment must include: Goal, Design decisions, File layout, Test plan,
Example usage. Do **not** proceed to Step 3 until the comment is posted.

---

## Step 3 — Implement the change

Edit only the target resource block(s). Do not touch unrelated code.

For all patterns (count/for_each guards, `try()` usage, `triggers`, naming rules,
azuread deprecations) see [ref-implementation-patterns.md](ref-implementation-patterns.md).

Key rules:
- Never remove or rename existing arguments.
- New optional arguments: use `try(var.x, <provider_default>)`.
- `triggers` blocks: add alongside existing `depends_on`, never replace it.
- After adding a conditional `for_each` on a module: grep all callers and wrap
  every external reference in `try()` before proceeding.

---

## Step 4 — Write a pure-logic test fixture

Create a fixture that exercises changed logic without provider credentials.
See [ref-test-fixture-templates.md](ref-test-fixture-templates.md) for full templates.

```
tests/fixtures/<feature_name>/
  main.tf                    # pure locals + outputs, no providers
  <feature_name>.tftest.hcl  # plan-time assertions
```

**Minimum test set:** (1) feature disabled → `count == 0`, (2) feature enabled →
`count == 1`, (3) new expression produces expected value, (4) edge case.

**Key rules:** `terraform { required_version = ">= 1.2.6" }` required; no
`provider` or `resource` blocks; each `local` comments the source file it mirrors;
output declarations in fmt-canonical format (re-read after `terraform fmt` before editing).

---

## Step 5 — Wire test discovery

If `tests/Makefile` does not exist, create it using the template in
[ref-makefile-template.md](ref-makefile-template.md). If it already exists, the
glob `fixtures/*/main.tf` auto-discovers new suites — no edits needed.

---

## Step 6 — Run the full validation cycle

Run in this exact order. Stop on first failure.

```bash
# 1. Run tests
cd tests && make test

# 2. Format
cd ..
terraform fmt -recursive

# 3. Lint
tflint --recursive

# 4. Check deprecation warnings (run from module root)
TF_DATA_DIR="$(mktemp -d)" terraform init -backend=false -input=false -no-color >/dev/null && \
TF_DATA_DIR="$TF_DATA_DIR" terraform validate 2>&1 | grep -i 'deprecat\|warning' || true
```

**Workspace-cleanliness guard:** always use a temporary `TF_DATA_DIR` for init/validate
to avoid `.terraform/` and `.terraform.lock.hcl` noise in the repo root. Remove any
artifacts before reporting completion.

**Guard — editing fixture files after fmt:** `terraform fmt` rewrites whitespace.
If you edit a fixture after fmt, re-read it first — use the post-fmt content as `oldString`.

**tflint warnings:** fix warnings from your changes; report pre-existing ones but
don't modify unrelated code. Never add ignore rules without user approval.

**Deprecation warnings from validate:** any `Warning: Argument is deprecated` in a
file you changed must be fixed. See [ref-implementation-patterns.md](ref-implementation-patterns.md)
for the `end_date_relative` fix.

---

## Step 7 — Update RELEASE_NOTES.md

Prepend a new entry using `YYYYMMDD.N` format:

```markdown
## 20260525.0

- Add `triggers` to `azurerm_virtual_network_peering` so peering re-syncs when address space changes.
- Add `tests/fixtures/vnet_peering_triggers/` with 6 plan-time tests.
- Add `tests/Makefile` with auto-discovering `test` target.
```

**Rules:**
- Newest entry at top. One bullet per logical change (not per file edited).
- **Avoid sub-release churn:** consolidate all iterations within a session into one
  entry. Only create a new numbered entry if changes are genuinely independent.
- **If ADO WI is in context:** post a completion comment after updating RELEASE_NOTES
  (proactively, for every edit including follow-on changes). See [ref-ado-workflow.md](ref-ado-workflow.md).
  Include: what changed, design decisions made and rejected, test count, release note entry.
- **If the implementation required a design pivot:** call it out explicitly in the
  completion comment — don't leave stale plan comments as the last record of intent.

---

## Step 8 — Create ESLZ documentation (mandatory when a new variable is introduced)

If the change introduces a new top-level `variable` set via tfvars, create or
update `ESLZ/<variable_name>.tfvars`. See [ref-eslz-template.md](ref-eslz-template.md)
for the template.

Required content: header comment, minimal example, full-featured example, inline
comments for non-obvious fields, valid scope/RG notes.

Run `terraform fmt` on the file. Create `ESLZ/` directory if it doesn't exist.

---

## Step 9 — Final completeness sweep (mandatory)

Verify every artifact **actually exists on disk** before declaring done:

```bash
ls -la <new_files_created>
head -5 RELEASE_NOTES.md
ls ESLZ/*.tfvars 2>/dev/null
cd tests && make test 2>&1 | tail -5
```

---

## Checklist

- [ ] Provider docs read for the exact version in use
- [ ] Existing arguments and `depends_on` preserved unchanged
- [ ] New argument uses `try()` or a safe default for backward compat
- [ ] Test fixture has `terraform { required_version = ... }`, no provider blocks
- [ ] Tests cover: disabled (count=0), enabled (count=1), new behaviour, edge case
- [ ] `make test` passes from `tests/`
- [ ] `terraform fmt -recursive` produces no diff
- [ ] `tflint --recursive` introduces no new warnings vs. before the change
- [ ] RELEASE_NOTES.md updated with entry at the top
- [ ] ESLZ tfvars example created/updated (when new variable introduced)
- [ ] Final completeness sweep run — all artifacts confirmed on disk
