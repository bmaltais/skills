---
name: audit-docs
description: >
  Audit a codebase's documentation (README, SKILL.md, AGENTS.md, etc.) for gaps
  against the actual implementation. Finds undocumented commands, flags, config
  fields, and behaviors. Use when a feature has landed but docs weren't updated,
  after a session where docs drift was discovered, or as a pre-release check.
categories: [documentation, quality, workflow]
agents: [pi, hermes, claude, copilot]
version: 1.0.0
---

# audit-docs

Audit documentation against implementation to find gaps, then fix or report them.

## Trigger Phrases

Use this skill when someone says:
- "audit the docs", "check if docs are up to date", "are the docs current?"
- "what's missing from the README / SKILL.md?"
- "docs might be out of date"
- after any feature PR is merged and no doc update was included

## Step 1 — Locate the Implementation Surface

Identify what the code actually exposes. For each project type:

| Project type | Where to look |
|---|---|
| **CLI (Go/Cobra)** | Grep all `Use:`, `Short:`, `Long:`, `Flags()` in `cmd/**/*.go` |
| **CLI (Python/Click/Typer)** | Grep `@app.command`, `@click.command`, `Option(`, `Argument(` |
| **Library** | Grep exported symbols (`^func [A-Z]`, `^type [A-Z]`, `^var [A-Z]`) |
| **REST API** | Grep route registrations (`router.GET`, `app.get(`, `@app.route`) |
| **Config structs** | Grep struct fields with `yaml:`, `json:`, `env:` tags |

Collect the full list. This is the **source of truth**.

## Step 2 — Locate the Docs Surface

Find all documentation files that describe the project's interface:

```bash
find . -name "README*" -o -name "SKILL.md" -o -name "AGENTS.md" \
       -o -name "*.md" -path "*/docs/*" | grep -v node_modules | grep -v .git
```

Read each file and extract what it documents: commands, flags, config keys, endpoints.

## Step 3 — Diff

Compare Step 1 vs Step 2:

- **Undocumented** — exists in code, absent from docs → must add
- **Stale** — in docs but removed from code → must remove or mark deprecated
- **Mismatch** — documented with wrong flag name, wrong default, wrong description → must correct

Build a table:

| Item | Status | File to fix |
|------|--------|-------------|
| `skillpack fork` | undocumented | README.md, SKILL.md |
| `--llm` flag on `update` | undocumented | README.md, SKILL.md |
| `skillpack self-update` | undocumented | README.md, SKILL.md |

## Step 4 — Prioritize

Fix in this order:
1. **Undocumented commands / flags** — users can't discover them
2. **Stale docs** — mislead users
3. **Mismatches** — minor but confusing

Skip items that are clearly internal/private (unexported, prefixed with `_`, marked `// internal`).

## Step 5 — Fix

For each gap:
- Read the current doc file before editing
- Add the missing item in the correct section (don't append at end)
- Match the surrounding style (table vs code block vs prose)
- For a new command, follow the existing command entry format exactly

## Step 6 — Verify

After edits:
```bash
# Re-run the grep from Step 1 and confirm all items appear in docs
grep -h "Use:" cmd/**/*.go | sort   # example for Cobra CLI
```

Manually spot-check two or three entries to confirm correct placement and formatting.

## Step 7 — Commit

```bash
git add <changed doc files>
git commit -m "docs: document <X>, <Y>, <Z>"
```

If a PR is already open for the feature, push onto that branch. Otherwise open a dedicated `docs/<feature-name>` branch and PR.

## Common Patterns by Project Type

### Cobra CLI (Go)

```bash
# Extract all command names and flags
grep -rh 'Use:\|\.Flags()\.' cmd/ | grep -v '//'

# Check which ones appear in README
grep -o '`skillpack [^`]*`' README.md | sort -u
```

### Python CLI (Typer/Click)

```bash
python -m myapp --help           # runtime help as ground truth
grep -rn "@app.command\|Option(" src/
```

### Config struct drift

```bash
# Find all yaml-tagged fields
grep -rn 'yaml:"' internal/config/
# Check which appear in README config section
```

## Notes

- Run this after every feature PR before closing it, or as part of a release checklist.
- If the project has a `plan.md` or `AGENTS.md`, check those too — they often go stale.
- Don't document internal helpers, only the public interface users or agents interact with.
