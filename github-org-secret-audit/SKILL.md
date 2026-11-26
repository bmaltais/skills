---
name: github-org-secret-audit
description: 'Audit a GitHub organization for leaked secrets and sensitive data across ALL repositories and FULL commit history, then produce a redacted single-page HTML report with severity-ranked findings and permalinks to the exact commit, file and line. Use when: scan org for secrets, sensitive data review, credential leak audit, gitleaks across repos, check old commits for passwords/keys, Terraform state committed, security review report, secret exposure audit, "make sure there is no sensitive info in our repos".'
argument-hint: 'GitHub org name (e.g. ssc-spc-cloud-nuage) and optional output folder'
---

# GitHub Organization Secret Exposure Audit

Defensive workflow: inventory every repo in an org, mirror-clone them (all refs), scan full history with Gitleaks, run a manual review for what default rules miss, triage, and publish a **redacted** HTML report with direct evidence links.

## Non-negotiable rules
- **Never print, echo or paste a secret value** into chat, terminal output you read back, or the report. Refer to values only by repo/path/commit/line/type and a `sid` (first 10 hex chars of SHA-256 of the value).
- Do not read `reports\*.json` (raw Gitleaks output) or mirror contents into the conversation; process them in scripts and only read redacted outputs.
- Do not test credentials against live services, rotate anything, rewrite history, or push. Recommend those actions.
- Tell the user that the work folder (`mirrors\`, `reports\*.json`) contains live secrets and must be kept private and deleted afterwards.
- Before placing the report in a git repo or public location, warn that it maps where live secrets are.

## Prerequisites
- `git` and Gitleaks (8.30+). Install with `winget install --id Gitleaks.Gitleaks -e --scope user` (ask first). The exe lands under `$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gitleaks.Gitleaks_*\gitleaks.exe` and is not on PATH in the current session.
- Unauthenticated API sees public repos only. For private/internal repos the user must set `$env:GITHUB_TOKEN` themselves (never ask for the token in chat).

## Procedure
Work folder default: `$HOME\org-secret-scan-<org>`. Run each script with the full path to Windows PowerShell:
`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File <script> -Org <org> -Root <folder>`

1. **Inventory**: [inventory.ps1](./scripts/inventory.ps1) writes `repos.json` (name, visibility, archived, fork, default branch). Report counts to the user.
2. **Mirror + scan**: [scan.ps1](./scripts/scan.ps1) does `git clone --mirror` for each repo, then Gitleaks `git` mode with `--log-opts="--all --full-history -m --root --no-ext-diff --no-textconv" --ignore-gitleaks-allow`. Writes `scan-summary.json` plus per-repo `reports\<repo>.json` and `.log`. Verify every repo has `scanExit` 0 or 2 and a scanned-commit count. A failed scan is **not** a clean result.
3. **Triage (redacted)**: [analyze.ps1](./scripts/analyze.ps1) writes `analysis.txt`, which groups matches by repo/rule/file/sid with shape (length and character classes), entropy, and whether the value is at default-branch HEAD.
4. **Manual review**: [manual-review.ps1](./scripts/manual-review.ps1) writes `manual-review.txt`. It covers sensitive file types in history (tfstate, .env, keys, kubeconfig and similar), password/key literals the rules miss (`LIT` lines), Terraform state attribute profiling, `.env` variable names, value presence on branch tips, and PII/ID counts.
5. **Classify** using [triage guide](./references/triage-guide.md): group raw matches into a few findings, rate severity and confidence, and separate false positives (placeholders, `index_key`, variable references, upstream fork defaults).
6. **Write the report** from [report-template.html](./assets/report-template.html). Sections are: header badges, executive summary with an immediate-priority callout, findings (High → Low), scope and methodology, automated scan disposition, remediation plan, and repository inventory. Fill in only facts you verified.
7. **Evidence appendix**: [evidence.ps1](./scripts/evidence.ps1) `-Report <html>` injects **Appendix A**, with permalinks for values still on default branches, and **Appendix B**, which lists every commit, file and line in history. Links use `https://github.com/<org>/<repo>/blob/<full-sha>/<path>#L<line>`. Confirm `evidence-status.txt` shows `emptyFile=0`.
8. **Deliver**: copy the HTML to the folder the user asks for (default `$HOME`). Summarize the counts and top risks, and remind the user about the private work folder.

## Environment pitfalls (learned the hard way)
- **PS 5.1 stderr**: native tools' stderr becomes ErrorRecords. With `$ErrorActionPreference='Stop'`, or inside `try`, that aborts on Gitleaks `INF` log lines. Run Gitleaks with `Start-Process -RedirectStandardError/-RedirectStandardOutput -Wait -PassThru` and read `.ExitCode`.
- **Bare mirrors** are rejected as "dubious ownership". Set this per process, without touching the global config: `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=safe.directory`, `GIT_CONFIG_VALUE_0=*`.
- **JSON arrays in PS 5.1**: `foreach ($i in @(Get-Content f -Raw | ConvertFrom-Json))` yields ONE item that holds the whole array. Assign to a variable first: `$a = Get-Content f -Raw | ConvertFrom-Json; foreach ($i in $a)`.
- **Alias shadowing**: never name helper functions `H`, `h`, `r`, `gc`, `sc`, `ls` and so on. Aliases win over functions, so `H` silently ran `Get-History`.
- `>` redirection in PS 5.1 writes UTF-16. Use `Set-Content -Encoding UTF8` inside scripts.
- The agent terminal can lag, lose PATH (cmdlets "not recognized"), or report "no output" while the script still runs. Always call powershell.exe by full path with `-File`. Have scripts write status files. If file-reading looks stale, verify with `cmd /c type <file>` or `findstr`.
- Gitleaks `generic-api-key` catches Terraform `index_key` (for_each keys) and similar non-secrets. Default rules miss many plain `password = "..."` literals, which is why the manual review is required.
