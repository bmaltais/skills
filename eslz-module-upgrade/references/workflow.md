# Upgrade Workflow

Use when: starting an ESLZ module upgrade — follow steps in order.

---

```
FUNC upgrade(module_path: str, target_version: str) -> None:
  gather_state(module_path)    # Step 1
  fetch_docs(target_version)   # Step 2
  gap_analysis()               # Step 3
  compat_check()               # Step 4
  implement()                  # Step 5
  validate()                   # Step 6
  artifacts()                  # Step 7
  lesson()                     # Step 8

FUNC gather_state(path: str) -> None:
  # Read ALL .tf files: providers.tf, variable.tf, locals.tf, name.tf, module.tf, output.tf
  # Read ESLZ/: <resource>.tf (module block), *.tfvars
  # Note: which args exposed, defaults, hardcoded vs variable-driven

  # CRITICAL: providers.tf must exist with required_providers; create before any change
  # Without it: callers on wrong major version break silently; README shows "No requirements"
  # Template: templates/providers.tf
  #   Substitute __PROVIDER_NAME__ and __PROVIDER_MAJOR__
  #   Add one required_providers block per provider in .terraform.lock.hcl
  #   Works for azurerm, azuread, azurestack, random, tls, or any other provider

  # CRITICAL: .tflint.hcl must exist; create if absent
  # Template: templates/.tflint.hcl — copy verbatim, no substitution needed
  # The `module` attribute was removed in tflint >= v0.54.0; use `call_module_type = "local"` instead
  # If .tflint.hcl already exists, verify it uses `call_module_type = "local"` not `module =`
  # Audit git history BEFORE touching any file
  sh("git log --oneline -20")
  # Look for: "Removed variables", "New naming convention", "Renamed", "Breaking"
  sh("git show <sha> -- variable.tf name.tf locals.tf")  # per suspicious commit

  GIT_RED_FLAGS = {
    "variable_removed":           "Callers fail plan → restore with default = null",
    "naming_convention_changed":  "Resources destroyed+recreated → Pattern 10 fallback",
    "resource_renamed_no_moved":  "State drift → add moved block",
  }

  # Read L2 caller contract: ESLZ/*.tf module block (not just tfvars)
  # Every arg in module block must exist in variable.tf
  sh("grep -E '^\\s+\\w+ ' ESLZ/*.tf")   # what caller passes
  sh("grep '^variable' variable.tf")       # what module declares
  # Gap → add as type = string (or any), default = null

  # CRITICAL: check child module versions — extract every `module` block source ref
  # For each `source = "github.com/<org>/<repo>.git?ref=<tag>"` found in *.tf:
  sh("grep -hE 'source\\s*=.*github\\.com' *.tf ESLZ/*.tf")  # list all child modules
  # For each repo, check latest release:
  sh("gh release view --repo <org>/<repo> --json tagName -q .tagName")
  # If latest > pinned: bump the ref= tag. Re-run terraform init -upgrade after bumping.
  # Note: storage/networking child modules may themselves have been upgraded to align
  # with the same target azurerm version — outdated pins silently pull old provider deps.

FUNC fetch_docs(target_version: str) -> None:
  # Fetch raw GitHub markdown (registry needs JS, cannot WebFetch):
  url = "https://raw.githubusercontent.com/hashicorp/terraform-provider-azurerm/refs/heads/main/website/docs/r/<resource>.html.markdown"
  # Record: required args, optional args, nested blocks, deprecations

FUNC gap_analysis() -> GapReport:
  CATEGORIES = {
    "Bug":     "wrong/will error for valid inputs → fix first",
    "Missing": "provider supports, module doesn't expose → add Phase 2",
    "Partial": "exposed but incomplete block → fix Phase 1",
    "OK":      "correctly implemented → no change",
  }
  COMMON_BUGS = [
    "hardcoded required block that provider marks optional (e.g. dns_config {} always emitted)",
    "single-port arg when provider accepts a set of ports",
    "merge(x, y) with no try() on x — crashes if key absent",
    "subnet_ids always set — breaks when ip_address_type = None",
    "regex [^\\/] — \\/ is invalid Terraform escape; use [^/]",
    "can(tolist(x)) ? x : [x] — branches must be same type; use try(tolist(x), [x])",
    "output references full resource object without sensitive = true",
  ]

FUNC compat_check() -> None:
  # For every proposed change, all of these must hold:
  ASSERT current_eslz_tfvars_produces_same_plan()    # callers must not need changes
  ASSERT no_resource_address_change() OR moved_block_added()
  ASSERT "ESLZ/*.tf module block still passes plan with no caller changes"
  ASSERT resource_name_unchanged() OR pattern10_fallback_added()
  # See compat-patterns.md for HCL patterns

FUNC implement() -> None:
  # Phase 1: Bug fixes (zero compat risk)
  # Phase 2: Additive new args/blocks (all gated with try(..., null))
  # Phase 3: Housekeeping (provider version pins, output sensitive flags)
  # Write entire file in one pass — line-by-line edits on large files → tool errors

FUNC validate() -> None:
  # Create tests/<resource>.tftest.hcl if absent (see references/testing.md)
  # Min runs: naming_convention, default_values, +1 per new argument added
  sh("terraform fmt -recursive")     # must produce no output
  sh("terraform init -backend=false")
  sh("terraform validate")           # must print "Success! The configuration is valid."
  sh("terraform test")               # must print "N passed, 0 failed"
  sh("tflint --init")                # download plugins declared in .tflint.hcl
  sh("tflint --recursive")           # must produce no output (zero findings)

FUNC artifacts() -> None:
  # Ten artifacts always required (all file templates in templates/):
  # 1.  .gitignore                           â templates/.gitignore
  # 2.  .gitattributes                       â templates/.gitattributes
  # 3.  .tflint.hcl                          â templates/.tflint.hcl (copy verbatim)
  # 4.  providers.tf                         â templates/providers.tf
  # 5.  ESLZ/<resource>.tfvars               â templates/ESLZ/module.tfvars
  # 6.  ESLZ/<resource>.tf (module block)    â templates/ESLZ/module.tf
  #     Check: ls ESLZ/*.tf â if absent, CREATE IT. Callers copy this into their L2 blueprint.
  # 7.  README.md                            â run terraform-docs after all changes
  # 8.  .github/workflows/documentation.yml â templates/.github/workflows/documentation.yml
  # 9.  .github/workflows/terraform-ci.yml  â templates/.github/workflows/terraform-ci.yml
  # 10. tests/upgrade_compat.tftest.hcl     â templates/tests/upgrade_compat.tftest.hcl
  # See eslz-artifacts.md for full token substitution table and per-artifact instructions

    # CRITICAL: verify GH Actions versions BEFORE writing workflow files — they go stale
  sh("gh release view --repo actions/checkout          --json tagName -q .tagName")
  sh("gh release view --repo hashicorp/setup-terraform --json tagName -q .tagName")
  sh("gh release view --repo terraform-docs/gh-actions --json tagName -q .tagName")
  # Update every uses: <action>@<version> to the returned tag

FUNC lesson() -> None:
  sh("""uv run python tools/lesson.py <resource-type> \
    --moved-blocks <yes/no> --test-count <N> \
    --notes "<non-obvious decisions or provider quirks>" """)
```


## .gitignore

Template: `templates/.gitignore` — see eslz-artifacts.md Artifact 7 for merge rules.

**Critical order**: `*.tfvars` must appear BEFORE `!ESLZ/*.tfvars` — a negation without a prior ignore rule is a no-op.
