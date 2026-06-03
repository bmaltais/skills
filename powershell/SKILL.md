---
name: powershell
description: >
  PowerShell cmdlet and scripting best practices based on Microsoft guidelines.
  Use when writing or reviewing PowerShell scripts (.ps1, .psm1). Trigger on
  phrases like "write a PowerShell function", "review my script", "PowerShell
  best practices", "cmdlet design", "PS1 style".
applyTo: '**/*.ps1,**/*.psm1'
categories: [software-development]
agents: [copilot]
version: 1.0.0
metadata:
  source: custom
  scope: global
---

# PowerShell Cmdlet Development

Write idiomatic, safe, and maintainable PowerShell aligned with Microsoft guidelines.

## Routing Table

| Topic                                         | Reference                    |
| --------------------------------------------- | ---------------------------- |
| Naming (verbs, params, variables, aliases)    | `references/naming.md`       |
| Parameter design (types, validation, switches) | `references/parameters.md`  |
| Pipeline, output, and PassThru patterns       | `references/pipeline.md`     |
| Error handling, ShouldProcess, safety         | `references/errors.md`       |
| Style, documentation, and performance         | `references/style.md`        |

## Key Rules (Always Apply)

- **Verb-Noun** format with approved verbs (`Get-Verb`), PascalCase, singular nouns.
- **`[CmdletBinding()]`** on every function — enables common parameters.
- **`[switch]`** for boolean flags — never `[bool]`, never assign defaults.
- **Exec form** for CMD/ENTRYPOINT in containers, **exec form** analogy: always use full cmdlet names, never aliases in scripts.
- **Non-interactive** — no `Read-Host`; accept all input via parameters.
- **Return objects** — never formatted text. Use `[PSCustomObject]` for structured data.
- **`SupportsShouldProcess`** on any function that modifies state.
- **Full names** — no aliases (`Get-ChildItem` not `gci`, `Where-Object` not `?`).
- **Comment-based help** (`.SYNOPSIS`, `.DESCRIPTION`, `.PARAMETER`, `.EXAMPLE`) on public functions.
