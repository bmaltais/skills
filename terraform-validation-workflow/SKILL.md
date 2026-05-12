---
agents:
    - copilot
categories:
    - software-development
description: Run the standard validation workflow for Terraform module repositories. Trigger when users ask to "validate", "lint", "run checks", "verify Terraform changes", "check this module", or "run terraform validation".
license: MIT
metadata:
    github-path: terraform-validation-workflow
    github-ref: refs/tags/v1.0.0
    github-repo: https://github.com/bmaltais/skills
    github-tree-sha: e4ec7e3cb42fa135add61d231a02f6193034c267
    scope: global
    source: custom
name: terraform-validation-workflow
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
