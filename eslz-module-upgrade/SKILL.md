---
agents:
    - copilot
categories:
    - software-development
description: Updates an existing ESLZ Terraform module to match a target provider version spec. Use when asked to upgrade, update, or bring a Terraform module up to spec with a provider version, when adding missing provider arguments to an existing ESLZ module, or when a user says "update this module", "bring it up to spec", or "add missing provider args". Also reviews and upgrades all dependent resources referenced in the module.
license: MIT
metadata:
    github-path: eslz-module-upgrade
    github-ref: refs/tags/v1.0.0
    github-repo: https://github.com/bmaltais/skills
    github-tree-sha: 86f113ecf84fd267539d158bb09184bc3507ec48
    scope: global
    source: custom
name: eslz-module-upgrade
---
# ESLZ Module Upgrade

Upgrades an existing ESLZ Terraform module to match provider documentation without breaking existing deployments. Includes comprehensive review and upgrade of all resources used and referenced within the module.

## Mandatory first action

**If the target azurerm provider version is not explicitly stated by the user, stop and ask:**

> "Which version of the azurerm provider should I target for this upgrade? (e.g. `3.117.0`, `4.x`, or `latest`)"

Do not proceed until the target version is confirmed. Once confirmed, record it and use it for all `recall.py` calls, `required_providers` constraints, and gap analysis throughout the workflow.

```bash
# Primary resource discover
uv run python tools/recall.py <resource-type>

# Discover all dependent resources
grep -r "resource \"" <module-path>/*.tf | awk -F':' '{print $2}' | grep -oE 'resource "[^"]+' | sort -u
```

## Routing table

| Task                                                      | Read                              |
| --------------------------------------------------------- | --------------------------------- |
| Full upgrade workflow (fetch, gap analysis, implement)    | `references/workflow.md`          |
| **New module from scratch** (no existing code to upgrade) | Same as upgrade workflow but skip gap analysis; focus on hierarchy-first design (see Key Invariants) |
| Backward compat HCL patterns (try, dynamic, moved, types) | `references/compat-patterns.md`   |
| Verbatim HCL templates for common upgrade cases           | `references/hcl-patterns.md`      |
| **N:M nested resource flattening** (e.g. N pools → M volumes) | `references/hcl-patterns.md` — "N:M flatten pattern" section |
| Terraform test structure (mock_provider, assertions)      | `references/testing.md` — or delegate to `tftest` skill if present |
| ESLZ artifacts (README, tfvars examples, CI workflow)     | `references/eslz-artifacts.md`    |
| Multi-resource upgrade (review all resources in module)   | `references/resource-discovery.md`|
| tflint config and version constraints                     | `references/workflow.md` — or delegate to `tflint` skill if present |
| File scaffolding (providers.tf, .gitignore, workflows, etc.) | `templates/` — read files directly, substitute tokens per `references/eslz-artifacts.md` |

## Dependent Resource Discovery & Upgrade

Before upgrading the primary resource, systematically discover and upgrade ALL resources used in the module:

1. **Identify all resource types** in module `.tf` files
2. **For each resource**, run `uv run python tools/recall.py <resource-type>` to get provider schema
3. **Gap analysis**: Compare each resource's current args to target provider version spec
4. **Dependency order**: Upgrade resources with no dependencies first, then downstream resources
5. **Validate references**: Ensure all `resource.*` references and `data.*` lookups remain valid
6. **Test coverage**: Add tftest assertions for each resource type's critical paths

### Multi-Resource Upgrade Workflow

**Phase 1: Discovery**
- Extract all `resource "` and `data "` blocks from module `.tf` files
- Create a resource dependency graph (which resources reference which)
- Identify isolated vs. integrated resource chains

**Phase 2: Gap Analysis (per resource)**
- Run `recall.py` for each resource type found
- Document old args, removed args, new args (with defaults)
- Flag breaking changes per resource
- Identify cross-resource arg renames (e.g., if `azurerm_network_interface` changes primary NIC field)

**Phase 3: Upgrade Order**
- Start with **leaf resources** (no refs from other resources in module)
- Then **intermediate resources** (referenced by others but don't ref others)
- Finally **root resources** (reference all others, e.g., main VM resource)
- Rationale: Ensures argument stability before consuming resources reference it

**Phase 4: Implementation (per resource tier)**
- Apply `try()`, `dynamic`, `moved`, `lifecycle.ignore_changes` patterns
- Update all downstream refs if resource arg names changed
- Add new tftest cases for new/changed arguments
- Verify module outputs still expose correct attributes

**Phase 5: Validation**
- `terraform fmt` all files
- `terraform validate` (catches type/ref errors across all resources)
- `terraform test` (all test files, all resource types)
- Manually review: do all tfvars examples still work for each resource?

**Phase 6: Documentation**
- Update README to show primary + major support resources (e.g., "Creates VM + NICs + disks")
- Comment tfvars examples for each new argument (across all resources)
- Document breaking changes and compat paths (if any)

## Key invariants (always enforce)

- **Audit git history first** — before any change, run `git log --oneline -20` and check for recently removed variables or naming convention changes that may already be breaking callers. Fix those first.
- **Discover all resources in module** — run resource discovery to identify every `resource` and `data` block. Do not assume only one resource type exists. Create a dependency graph: resources with no dependencies → downstream resources.
- **Upgrade ALL resource types** — for each resource discovered, gap-analyze against target provider version. Never skip secondary/support resources (e.g., if upgrading azurerm_linux_virtual_machine, also upgrade azurerm_network_interface, azurerm_managed_disk, etc.). Apply upgrade patterns to all.
- **Validate cross-resource references** — ensure all `aws_*`, `azurerm_*`, `data.provider_*` references between resources remain valid. If a resource's argument name changed, update all downstream references. Check module outputs that expose resource attributes.
- **Read the L2 caller contract** — always read `ESLZ/*.tf` (the module block, not just tfvars) to discover every argument the caller passes. The module interface must accept all of them for ALL resources.
- **Never remove module input variables** — if a variable was removed in a prior commit, restore it as optional (`default = null`). Callers passing it must not fail.
- **Naming convention changes need a compat path** — if the naming formula changed (on primary or any resource), implement a three-tier fallback: explicit override > legacy formula (when old vars present) > new convention. A naming change without a compat path forces resource replacement.
- **Every auto-generated resource name must have an optional override** — for every resource whose `name` is constructed from locals (VM, OS disk, NIC, NIC IP configuration, data disks, NSG, Key Vault secret, etc.), wrap it with `try(var.<config>.<name_field>, <generated_default>)`. This lets callers whose existing deployments diverge from the naming formula pin to their real names without destroy/recreate. Apply this on every new module and every upgrade. See `references/compat-patterns.md` Pattern 12 for the full HCL template and required tftest assertions.
- **`providers.tf` must exist and pin versions** — if absent or missing `required_providers`, create it before any other change. Constrain EVERY provider to `~> <major>.0`. Check `.terraform.lock.hcl` for the full provider list (including all providers for all resources in module). Without this, callers on a different major version break silently and README shows "No requirements".
- **Purge dead locals after resource removal** — whenever a resource or `name.tf` entry is deleted, grep all remaining `.tf` files for every `local.*` name defined in `locals.tf` (and `name.tf`). If a local is defined but never referenced, remove it. Then check whether the file that contained it is now empty (only `locals {}` with no assignments) — if so, delete the file entirely. An empty `locals {}` block is valid HCL but meaningless noise; `terraform validate` will not warn about it.
- **Audit variable descriptions for copy-paste artifacts** — after any variable is added or edited, read its `description` field and verify it matches the resource being created. Descriptions like *"Cluster configuration for the HA VMs"* in a data lake module, or *"Storage account settings"* in a key vault module, are copy-paste leftovers. Rewrite to accurately name the resource type and its purpose (e.g., *"Data Lake Gen2 configuration including storage account and filesystem definitions"*).
- **Check child module versions** — grep all `module` blocks for `source = "github.com/...?ref=<tag>"`. For each, run `gh release view --repo <org>/<repo> --json tagName -q .tagName`. If the latest tag is newer than the pinned ref, bump it. Run `terraform init -upgrade` after. Child modules (e.g. storage account, private endpoint) are often upgraded to match the same azurerm target version — stale pins silently pull old provider constraints.
- **Bump `ESLZ/mssql.tf` (or equivalent) module ref** — the `source = "...?ref=<tag>"` inside `ESLZ/*.tf` must be updated to the next release version of this module before committing. Determine the next version from `git tag --sort=-v:refname | head -1` and increment: patch for bug-fix-only PRs, minor for any new arguments or features. Commit this change as a separate `chore: bump ESLZ module ref to vX.Y.Z` commit on the feature branch.
- **No backward compat breaks** — every change to existing arguments on ALL resources must continue to accept the current tfvars format.
- **`tests/` must cover all resources** — if `tests/<resource-type>.tftest.hcl` is absent for any resource, create it before running validate. If the `tftest` skill is present, delegate `.tftest.hcl` authoring to it rather than writing tests inline. Minimum runs per resource: `naming_convention`, `default_values`, one run per new argument added. `terraform test` must print `0 failed` before closing.
- **Write → validate → test (all resources)** — never skip `terraform fmt -recursive && terraform validate && terraform test && tflint --recursive`. Validate runs ALL resource types in module.
- **tflint must be configured and passing** — `.tflint.hcl` must exist at the module root. The `module` attribute was removed in tflint v0.54.0; use `call_module_type = "local"` instead. Run `tflint --recursive` after `terraform test`; it must produce no output (zero findings). If `.tflint.hcl` is absent or needs review, copy `templates/.tflint.hcl` (no substitution needed). If the `tflint` skill is present, delegate to it for plugin selection and rule tuning.
- **ESLZ artifacts are required** — `.gitignore` must exist (create if missing), `.tflint.hcl` must exist (create if missing), README must document ALL major resources in module block + tfvars pattern (not raw resource), tfvars must have commented examples for every new argument across all resources, tests must cover all resource types and integration paths, CI workflow must exist and include tflint steps.
- **`ESLZ/<resource>.tf` module block must exist** — run `ls ESLZ/*.tf` before closing. If the file is absent, create it: it declares one `variable` block per module input and a `module "<resource>"` block with `for_each = var.<resource>`, `source` pinned to the next semver tag, and every module variable passed through. This is the file L2 callers copy into their blueprint. Without it the module cannot be used. See `references/eslz-artifacts.md` Artifact 2 for the template.
- **`.gitignore` must use the standard template** — read the existing `.gitignore` before touching anything. Old modules often have a minimal file scoped to a `test/` subdirectory or Windows-specific paths. Replace it with `templates/.gitignore` (covers `.terraform/`, `*.tfstate`, `*.tfplan`, `crash.log`, override files, root `*.tfvars.json`; keeps `ESLZ/*.tfvars` tracked). **Critical**: `*.tfvars` must appear as an ignored pattern **before** `!ESLZ/*.tfvars` — a negation with no prior ignore rule is a no-op and will not protect secrets.
- **`.gitattributes` must enforce LF line endings** — check for `* text=auto eol=lf`. If absent or missing that line, add it. CRLF files silently break `replace_string_in_file` edits and `terraform fmt`; strip existing CRLF with `sed -i 's/\r//' *.tf` if needed before editing.
- **GitHub Actions versions must be current** — run `gh release view --repo <action> --json tagName -q .tagName` for every action in every workflow file before writing or committing. Never copy version pins from skill templates without verifying — they go stale. **When reviewing an existing workflow that appears to have a wrong version, verify FIRST before changing** — a CI failure with `git exit code 1` is more likely a transient network error or a bad `ref:` value than an invalid action version. Downgrading a correct pin wastes a commit and reintroduces the problem.
- **`documentation.yml` auto-commits terraform-docs on push — do not run it manually before pushing** — if the repo has a `.github/workflows/documentation.yml` workflow, the CI will run `terraform-docs` and commit the result automatically after `git push`. Running `terraform-docs` locally and committing before the push creates a non-fast-forward conflict because both the local commit and the Actions commit touch `README.md`. Skip the manual `terraform-docs` run (or skip the commit of it); pull after push to fast-forward if the CI already fired. Only run terraform-docs locally when the workflow does NOT exist or is disabled.
- **Hierarchy-first module design** — before writing any `.tf` code for a new module that wraps multiple tightly-coupled Azure resources (e.g. account → pool → volume, namespace → eventhub → consumer group), identify the correct root resource. The module's primary `var.<resource>` input variable must be keyed on the topmost resource (the one all others depend on). A module keyed on a leaf resource (e.g. `var.netapp_volume`) when a parent resource (account) is required forces callers to make N calls instead of 1 and creates a fundamental design flaw that cannot be fixed without breaking the API. Rule: the input variable key must correspond to the resource with no Azure-side parent within the module's scope.
- **N:M nested resources use `flatten` + composite keys in `locals.tf`** — when a module manages N parents that each own M children (e.g. N pools with M volumes), do NOT create a separate `for_each` variable per level. Instead, compute a flat map in `locals.tf` keyed by `"${parent_key}--${child_key}"` using the `flatten([for p in ... : [for c in ...]])` pattern. Use `--` as the delimiter (it cannot appear in Azure resource names). Reference the parent resource with `azurerm_<parent>.<label>[each.value._parent_key]`. See `references/hcl-patterns.md` — "N:M flatten pattern" for the verbatim template.
- **`name.tf` holds scalar names; `locals.tf` holds per-instance enriched maps** — scalar names that apply to the whole module call (account name, backup vault name) belong in `name.tf`. Names that vary per resource instance (pool name, volume name, policy name) must NOT be in `name.tf` — compute them as `_name` attributes inside the enriched `for` map in `locals.tf` so they are co-located with the instance config they describe. Mixing per-instance names into `name.tf` produces stale locals that go out of sync when the resource set changes.
- **SSC Azure Naming Standard v2.1 must be followed for all resource names** — the auto-generated name formula is `{env4}{serverType3}-{userDefinedString}` where: `env` is the 4-char GC prefix `<dept(2)><env(1)><region(1)>` (e.g. `ScPc` = SSC Production Canada Central), and `serverType` is the 3-char SACM device type that attaches **directly** to the prefix with no delimiter. The hyphen `-` separates the prefix block from `userDefinedString`. Never invent device type codes — use the standard table. Common codes: `CPS` = Cloud Platform Service (generic PaaS), `CNR` = Cloud Network Resource (VNets/NICs/NSGs), `CSV` = Cloud Secret Vault (Key Vault), `CSA` = Cloud Storage Account, `SWx`/`SLx` = Windows/Linux VM server types. If the `ssc-azure-naming` skill is present, delegate device-type lookup to it. See `references/hcl-patterns.md` — "SSC name.tf pattern" for the verbatim template. **Every new module and every upgrade must audit the `serverType` default and correct it if it does not match the standard.**
- **Resource outputs and sensitive values** — all module outputs that expose full resource objects must be `sensitive = true`. Mock providers surface nested sensitive values that break tests.
- **README must have static content above `<!-- BEGIN_TF_DOCS -->`** — terraform-docs erases everything inside the `<!-- BEGIN_TF_DOCS --> … <!-- END_TF_DOCS -->` markers on every run. The module title (`# module-name`) and one-line description must sit **above** the opening marker, not inside it. When rewriting README, always place the title/description first, then the marker block.
- **All files must end with a trailing newline** — after writing or editing any `.tf`, `.md`, `.yml`, or `.tfvars` file, verify the last byte is `\n`. This includes **pre-existing files that were not directly changed** — reformatting or tooling can silently lose trailing newlines. Run `find . \( -name "*.tf" -o -name "*.md" -o -name "*.yml" -o -name "*.tfvars" \) | xargs -I{} sh -c 'tail -c1 "{}" | xxd | grep -q "0a" || echo "Missing newline: {}"'` to audit the whole module before committing. Missing trailing newlines cause noisy diffs and fail some linters.

## Mandatory last action

```bash
# Document complete resource upgrade summary
uv run python tools/lesson.py <module-name> \
  --resources "<comma-separated list of all upgraded resources>" \
  --moved-blocks <yes/no> \
  --test-count <N> \
  --cross-resource-changes <yes/no> \
  --notes "<non-obvious decisions, e.g. dependency-driven upgrade order>"
```

## Quick decisions

| Situation                                         | Decision                                                             |
| ------------------------------------------------- | -------------------------------------------------------------------- |
| `ESLZ/<resource>.tf` absent                       | Create it: variable blocks + `module` block with `for_each`, `source = ...?ref=vNEXT`, all inputs passed through (see `references/eslz-artifacts.md` Artifact 2) |
| Resource / module renamed                         | Add `moved` block, keep old name as alias                            |
| Argument was `required`, now optional             | Wrap with `try(..., null)` — no state change                         |
| Argument was `optional`, now required             | Add validation or sensible default via `try()`                       |
| Block was always emitted, now conditional         | Convert to `dynamic` block — no impact on existing configs           |
| Input accepts single object OR list               | Normalize with `try(tolist(), [wrap])` in locals                     |
| Output references full resource object            | Add `sensitive = true`                                               |
| Variable was removed in a prior commit            | Restore with `default = null` — callers must not fail plan           |
| Naming convention changed in a prior commit       | Three-tier fallback: explicit override > legacy > new (see Pattern 10) |
| Auto-generated resource name may diverge from real infra | Add `try(<override_var>, <generated_default>)` to every `name =` that uses locals — see Pattern 12 |
| L2 caller passes args not in variable.tf          | Add those variables as optional (`default = null`)                   |
| Secondary resource arg name changed              | Update all refs in primary resource, outputs, and downstream logic   |
| Multiple resources need upgrade                  | Upgrade in dependency order: no-deps first, then refs to those       |
| `.gitignore` is minimal / scoped to `test/`      | Replace entirely with `templates/.gitignore` |
| `.gitignore` has `!ESLZ/*.tfvars` without `*.tfvars` above it | Negation is a no-op; add `*.tfvars` as an ignored pattern **before** the `!ESLZ/*.tfvars` line |
| `.gitattributes` missing `eol=lf`                | Add `* text=auto eol=lf`; strip CRLF from existing `.tf` files with `sed -i 's/\r//' *.tf` before editing |
| Module uses data source that changed             | Re-validate `data.provider_*` block args against target provider     |
| Cross-resource attr reference breaks             | Add `try()` wrapper or add new compat variable for old reference path|
| README title/description inside `<!-- BEGIN_TF_DOCS -->` | Move above the marker — terraform-docs overwrites everything inside it |
| File missing trailing newline                    | Ensure every created/edited file ends with `\n`; check with `tail -c1 file \| xxd` |
| CI checkout fails with `git exit code 1`         | **Verify the action version FIRST** with `gh release view --repo actions/checkout --json tagName -q .tagName` before changing anything — likely transient network or a bad `ref:` value, not a wrong version pin |
| Docs workflow fails with `git exit code 1` on PR | Trigger is `pull_request` from a fork; GitHub runs it in the base repo context so the fork's branch doesn't exist. Change trigger to `push` on main with `ref: ${{ github.ref }}` — use `templates/.github/workflows/documentation.yml` |
| `git push` rejected as non-fast-forward after manual terraform-docs commit | `documentation.yml` CI already committed the same README change. Run `git reset --soft HEAD~1 && git checkout -- README.md` to undo the local commit, then `git pull --ff-only` to sync. |
| `replace_string_in_file` succeeds but old content still appears below | The tool replaces only the **first matching occurrence** — content after the matched block is untouched. When rewriting a file where the old content spans the entire file, match the full file content or use `run_in_terminal` with `cat > file` to overwrite completely. Always verify with `wc -l` and `grep` after a file rewrite. |
| Module wraps N parents each with M children | Use the `flatten` N:M pattern in `locals.tf` (see Key Invariants and `references/hcl-patterns.md`). Never create separate `for_each` variables per level. |
| Module input variable is keyed on a leaf resource | Redesign: rekey on the topmost (root) resource. A leaf-keyed module forces N calls for 1 account and makes the hierarchy unmanageable. |
| `serverType` default is not a standard SSC SACM code | Replace with the correct code: `CPS` (generic PaaS), `CNR` (networking), `CSV` (Key Vault), `CSA` (storage), `SWx`/`SLx` (VMs). Delegate to `ssc-azure-naming` skill if unsure. |
| `env` variable description doesn't mention SSC 4-char prefix | Update to: `"(Required) 4-character SSC naming prefix: <dept(2)><env(1)><region(1)>, e.g. ScPc = SSC Production Canada Central. See SSC Azure Naming Standard v2.1."` |
| Resource name uses freeform `serverType` without SSC alignment | Audit against SSC device type table and correct before closing the PR. A wrong code is a governance violation that requires a rename (and state replacement) later. |
