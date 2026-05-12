---
agents:
    - copilot
categories:
    - software-development
description: Run the standard terraform-docs update workflow for Terraform module repositories when users ask to regenerate or update README docs.
license: MIT
metadata:
    github-path: terraform-docs-workflow
    github-ref: refs/tags/v1.0.0
    github-repo: https://github.com/bmaltais/skills
    github-tree-sha: 64fab43053a476d057b62222ff94078cfb56079c
    scope: global
    source: custom
name: terraform-docs-workflow
---
# Terraform Docs Workflow (Module Repo)

Use this workflow whenever README Terraform documentation needs to be generated or refreshed.

## Required sequence

1. Ensure `terraform-docs` is available:
   - Prefer existing binary on `PATH`.
   - If unavailable, use local user install at `$HOME/.local/bin/terraform-docs`.

2. Regenerate docs at repo root:
   - `terraform-docs markdown table --output-file README.md --output-mode inject .`
   - If not on `PATH`, use `$HOME/.local/bin/terraform-docs markdown table --output-file README.md --output-mode inject .`.

3. Verify injected output:
   - Confirm `<!-- BEGIN_TF_DOCS -->` and `<!-- END_TF_DOCS -->` remain present.
   - Confirm expected type rows in `README.md` match module variables after changes.
   - Confirm Requirements table reflects current version constraints (including upper bounds when defined).

## Execution guidance

- Keep the change limited to docs generation unless user asked for additional edits.
- If local install is required, avoid sudo and prefer `$HOME/.local/bin`.
- Report command used and whether install fallback was needed.

## Success criteria

- `README.md` is updated successfully via inject mode.
- TF docs markers are intact.
- Any changed variable types are correctly reflected in the Inputs table.
