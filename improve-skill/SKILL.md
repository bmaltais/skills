---
name: improve-skill
description: Review the current session and suggest improvements based on issues observed during the session.
argument-hint: "What specific areas or issues should the skill be improved in to make it more effective?"
---

# Improve Skill

Systematically identify friction points from the current session, map them to owning skills, and implement targeted fixes.

## Step 1 — Session Archaeology

Scan the session for friction signals:

| Signal | Example |
|--------|---------|
| User correction | "you forgot", "that's wrong", "this keeps happening" |
| Tool failure | failed replacement, build error, test failure that required repair |
| Re-reads | reading the same file twice (= stale context or forgotten content) |
| Skipped steps | plan not updated, tests not run, commit without push |
| Extra round-trip | clarifying question that revealed an unspoken requirement |
| Repeated pattern | same fix applied multiple times in one session |

List every signal. Don't filter yet.

## Step 2 — Categorize

For each signal, assign a category:

- `accuracy` — wrong output or misunderstood requirement
- `coverage` — missing edge case, feature gap
- `UX` — confusing output or poor error message
- `reliability` — tool failure, wrong oldString, broken tool call
- `workflow` — skipped step, wrong ordering, forgotten checklist item

## Step 3 — Prioritize

Rank by **impact × frequency**:

- **High impact + high frequency** → fix immediately
- **High impact + low frequency** → fix if the change is small
- **Low impact** → skip

Report the ranking before implementing.

## Step 4 — Identify Owning Skill

For each prioritized issue, name the skill that governs the broken behavior. If multiple skills overlap, pick the most specific one. If no skill owns it, check `~/.copilot/skills/` and `~/.claude/skills/` for candidates.

If the session does not clearly point to a specific skill, ask the user before proceeding.

## Step 5 — Implement

Read the owning skill file before editing it. Make the minimum change that addresses the root cause:

- Add a **mandatory step** for skipped workflow items
- Add a **guard / check** for reliability issues
- Add a **concrete example** for UX / accuracy issues
- Add a **decision rule** for coverage gaps

Label the change type in your explanation (e.g. "adding mandatory step").

### Beyond SKILL.md edits — scripts and reference files

When a skill involves multi-step shell workflows, also consider creating supporting artifacts alongside the SKILL.md:

- **Helper scripts** (`scripts/` subdirectory next to SKILL.md) — create a script when:
  - Steps are repeated across many sessions (amortises boilerplate)
  - Variables must persist across terminal invocations (script keeps them in scope)
  - An operation is destructive and needs a guaranteed cleanup/restore step (use `trap`)
  - The manual steps are error-prone enough that a single-command invocation materially reduces risk
- **Reference files** (`docs/` or inline in SKILL.md) — add a cheat-sheet or status-code table when:
  - The skill relies on an external API with non-obvious field values (e.g. policy evaluation statuses)
  - The same lookup (org/project IDs, endpoint formats) is performed every session

When adding scripts: make them executable (`chmod +x`), self-documenting (usage comment at top), and reference them from the "Preferred approach" section at the top of SKILL.md so the agent reaches for the script before the manual steps.

## Step 6 — Verify

After editing:
1. Re-read the changed section of the skill file.
2. Ask: "Would this change have prevented the observed failure?"
3. If yes → done. If no → revise.

## Notes

- Fix the root cause, not the symptom. If "plan.md was not updated" is the symptom, the root cause is "no step requires it" — add the step.
- One skill, one PR's worth of change per invocation. Don't batch improvements across unrelated skills.
- If the user passed a specific skill or instruction, treat it as the Step 4 answer and skip to Step 5.
- **Quality over quantity.** If the session produced no genuine friction — no user corrections, no tool failures, no re-reads, no skipped steps — report that clearly and stop. Do not invent improvements to appear productive. A session with zero skill changes is a good outcome if nothing actually broke.