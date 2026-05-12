---
agents:
    - copilot
categories:
    - software-development
description: Explain and recommend Terraform versioning best practices for required_providers and required_version in modules versus root stacks. Use this whenever the user asks about Terraform version constraints, provider pinning, whether to use >= or ~>, module compatibility policy, or how to structure versions.tf in reusable modules.
license: MIT
metadata:
    github-path: terraform-versioning-advisor
    github-ref: refs/tags/v1.0.0
    github-repo: https://github.com/bmaltais/skills
    github-tree-sha: 08feb1ebad58d37e08783a6a89f0b2de0722fa51
    scope: global
    source: custom
name: terraform-versioning-advisor
---
# Terraform Versioning Advisor

Use this skill to give precise, practical guidance for Terraform version constraints in `versions.tf`.

## Goals

- Clarify whether the configuration is a **reusable child module** or a **root/environment module**.
- Recommend safe, maintainable constraints for `required_providers` and `required_version`.
- Avoid contradictory guidance by explaining tradeoffs and defaults.

## Decision flow

1. Detect scope:
   - If code is a shared module consumed by other repos, treat as **reusable module**.
   - If code owns deployments/environments, treat as **root module**.

2. Always evaluate provider requirements:
   - Recommend explicit `source` and `version` for each required provider.
   - Explain that requirements belong in every module for clarity and dependency solving.

3. Evaluate Terraform CLI constraint:
   - Root modules: always include `required_version`.
   - Reusable modules: include `required_version` when language/features require a minimum version; keep bounds broad enough for consumers.

4. Recommend version-shape policy:
   - Avoid unbounded `>=` when major-version breakage risk matters.
   - Prefer bounded ranges for reusable modules (for example `>= x.y, < next-major`).
   - Prefer controlled upgrade strategy in roots (for example `~>` where appropriate).

## Output format

When giving recommendations, use this structure:

1. **Verdict**: is current pattern acceptable or risky?
2. **Why**: concise rationale (provider resolution, compatibility, upgrade safety).
3. **Suggested constraints**: concrete snippet(s) for module/root.
4. **Risk callout**: what breaks with unbounded `>=`.
5. **Next question**: ask whether this repo is module vs root if still ambiguous.

## Recommended snippets

### Reusable module (library-style)

```hcl
terraform {
  required_version = ">= 1.5.0, < 2.0.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.63.0, < 5.0.0"
    }
    time = {
      source  = "hashicorp/time"
      version = ">= 0.11.0, < 1.0.0"
    }
  }
}
```

### Root module (environment stack)

```hcl
terraform {
  required_version = "~> 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.63"
    }
  }
}
```

## Guardrails

- Do not add `provider "..."` configuration blocks to reusable child modules unless explicitly requested.
- Do not over-constrain reusable modules without a stated compatibility policy.
- Prefer minimal edits that preserve existing behavior and CI expectations.

## Example trigger prompts

- "Is `required_providers` inside a module best practice?"
- "Should we keep `required_version` in every module?"
- "Can you review this `versions.tf` and suggest safer constraints?"
- "Should this use `>=` or `~>` for azurerm?"
