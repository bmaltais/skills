---
name: terraform-validation-workflow
description: Run the standard validation workflow for Terraform module repositories. Trigger when users ask to "validate", "lint", "run checks", "verify Terraform changes", "check this module", or "run terraform validation".
categories: [software-development]
agents: [copilot]
license: MIT
metadata:
  source: custom
  scope: global
---

# Terraform Validation Workflow (Module Repo)

Use this workflow whenever validating changes in a Terraform module repository.

## Required sequence

1. Validate at repo root:
   - `terraform init -backend=false`
   - `terraform validate`

2. Validate in `test/` (if present):
   - `cd test && terraform init -backend=false && terraform validate`

3. Lint recursively from repo root:
   - `tflint --recursive`

## Execution guidance

- Run commands in the exact order above.
- Stop immediately on first hard failure and report the failing command and error.
- Keep implementation example directories (like ESLZ/) as user-facing examples and do not rely on them for local module validation.
- Keep changes minimal and do not modify unrelated files while validating.

## Success criteria

- Root `terraform validate` passes.
- `terraform validate` in `test/` passes (if test/ exists).
- `tflint --recursive` returns no issues.
