---
name: skill-doctor
description: >
  Split a large SKILL.md into a slim main file plus focused reference files,
  without losing any content. Use when a SKILL.md exceeds ~400 lines or has
  grown unwieldy. Trigger on phrases like "split this skill", "refactor this skill",
  "skill is too long", "reduce skill size", "extract reference files from skill",
  or "skill doctor".
categories: [agent-management]
agents: [copilot]
version: 1.0.0
metadata:
  source: custom
  scope: global
---

# Skill Doctor

Splits an oversized SKILL.md into a lean main file (≤ 400 lines) plus focused
reference files, with a mandatory completeness check to ensure nothing is lost.

---

## Step 1 — Read and measure the skill

```bash
wc -l <skill_dir>/SKILL.md
```

Read the **entire** file before touching anything. Note:
- Total line count
- The YAML frontmatter block (must stay in `SKILL.md`)
- Natural content boundaries (headings, sections, templates, code blocks)

If the file is under 350 lines, tell the user it doesn't need splitting and stop.

---

## Step 2 — Identify split candidates

Look for sections that are:
- **Self-contained templates or code blocks** (e.g. full HCL templates, Makefile
  snippets, shell scripts) — ideal for extraction
- **Reference material** read occasionally (patterns, edge cases, checklists with
  code) vs. **procedural steps** read every run
- **Step-specific deep-dives** that balloon a single step (e.g. "Step 4" with 80
  lines of fixture templates)

Propose the split plan to the user **before creating any files**:

```
Proposed split for <skill_name>/SKILL.md (<N> lines → ~<target> lines):

  ref-<topic-a>.md   (~XX lines)  — <one sentence description>
  ref-<topic-b>.md   (~XX lines)  — <one sentence description>
  ...

Main SKILL.md will retain: frontmatter, all step headings, key rules (summarized),
links to ref files.
```

Wait for user confirmation before proceeding.

---

## Step 3 — Capture the original for diffing

```bash
# Save a verbatim copy of the original SKILL.md for later comparison
cp <skill_dir>/SKILL.md /tmp/skill_doctor_original.md
wc -l /tmp/skill_doctor_original.md
```

This snapshot is the ground truth for the completeness check in Step 6.

---

## Step 4 — Create reference files

For each proposed ref file:
1. Create `<skill_dir>/ref-<topic>.md` with the extracted content.
2. Content must be **verbatim** from the original — do not paraphrase or trim.
3. Add a one-line header comment at the top: `# <Topic> Reference` so the file
   is self-explanatory when read in isolation.

Naming convention: `ref-<kebab-case-topic>.md`

Examples:
- `ref-implementation-patterns.md`
- `ref-test-fixture-templates.md`
- `ref-makefile-template.md`
- `ref-eslz-template.md`
- `ref-ado-workflow.md`

---

## Step 5 — Rewrite SKILL.md

Replace the original content with a slim version that:

- **Keeps the YAML frontmatter unchanged** (all keys, all values).
- **Keeps every step heading** — do not collapse or rename steps.
- **Keeps all mandatory rules inline** if they are short (≤ 5 lines). Rules that
  are long because of code blocks → extract the code block, keep the rule text.
- **Replaces extracted code blocks / templates** with a one-line pointer:
  `See [ref-<topic>.md](ref-<topic>.md) for the full template.`
- **Adds a reference index** near the top of the document body (after the intro
  paragraph, before Step 1):

```markdown
**Reference files** (load as needed):
- [ref-topic-a.md](ref-topic-a.md) — one-sentence description
- [ref-topic-b.md](ref-topic-b.md) — one-sentence description
```

Target: **≤ 400 lines**. If still over 400 after a first pass, identify the next
largest section and extract it too.

---

## Step 6 — Completeness verification (mandatory)

This step ensures no content was silently dropped.

### 6a — Extract all prose sentences from both versions

```bash
# Strip code fences, blank lines, markdown syntax — keep prose lines only
grep -v '^\s*```' /tmp/skill_doctor_original.md \
  | grep -v '^\s*$' \
  | grep -v '^\s*#' \
  | grep -v '^\s*[-*|]' \
  | grep -v '^\s*\.' \
  | sort > /tmp/orig_prose.txt

# Do the same across all files in the new split
cat <skill_dir>/SKILL.md <skill_dir>/ref-*.md \
  | grep -v '^\s*```' \
  | grep -v '^\s*$' \
  | grep -v '^\s*#' \
  | grep -v '^\s*[-*|]' \
  | grep -v '^\s*\.' \
  | sort > /tmp/new_prose.txt

diff /tmp/orig_prose.txt /tmp/new_prose.txt
```

Lines prefixed with `<` appear only in the original — **these are losses**.
Lines prefixed with `>` appear only in the new files — acceptable (added pointers).

### 6b — Verify code blocks

```bash
# Count fenced code blocks in original vs combined new files
grep -c '^\s*```' /tmp/skill_doctor_original.md
cat <skill_dir>/SKILL.md <skill_dir>/ref-*.md | grep -c '^\s*```'
```

The counts should be equal (or the new count slightly higher due to added ref-file
headers). If the original count is **higher**, a code block was dropped.

### 6c — Verify line totals

```bash
wc -l /tmp/skill_doctor_original.md
cat <skill_dir>/ref-*.md | wc -l
wc -l <skill_dir>/SKILL.md
```

`ref files total + new SKILL.md` should be **≥ original line count** (it will be
slightly higher due to added headers and pointer lines — that's expected).

If any check shows losses, go back and restore the missing content before reporting
done.

---

## Step 7 — Final check

```bash
wc -l <skill_dir>/SKILL.md
ls -la <skill_dir>/
```

Confirm:
- [ ] SKILL.md is ≤ 400 lines
- [ ] YAML frontmatter is unchanged (check `name`, `description`, `categories`, `version`)
- [ ] All ref files exist on disk
- [ ] Prose diff shows no losses (Step 6a)
- [ ] Code block count matches (Step 6b)
- [ ] Combined line total ≥ original (Step 6c)
- [ ] Each ref file has a `# <Title> Reference` header
- [ ] Reference index added to SKILL.md body

Report the final line count breakdown to the user:
```
SKILL.md:            248 lines  (was 620)
ref-patterns.md:      55 lines
ref-templates.md:    110 lines
ref-makefile.md:      28 lines
─────────────────────────────
Total:               441 lines  (original: 620) — no content lost
```
