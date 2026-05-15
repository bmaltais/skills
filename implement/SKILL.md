---
name: implement
description: Pick up a GitHub issue tagged ready-for-agent and implement it. Reads the agent brief, explores the codebase, writes the fix or feature, verifies all acceptance criteria, and opens a linked PR. Use when the user says "pick up an issue", "work on a ready-for-agent issue", "implement issue #N", "fix issue #N", "/implement", or wants to action a pre-triaged issue.
---

# Implement

Pick up a `ready-for-agent` issue from the tracker, implement it against the agent brief, verify every acceptance criterion, and ship a PR.

The **agent brief comment** is the contract. The original issue body is background. If they conflict, the brief wins.

## Invocation

```
/implement          — list ready-for-agent issues and let maintainer pick
/implement #N       — go straight to issue N
```

## Phase 1 — Discover

If no issue number was given, query the tracker:

```
gh issue list --label ready-for-agent --state open --json number,title,createdAt
```

Show issues oldest-first. Let the maintainer pick. If exactly one issue exists, confirm and proceed.

## Phase 2 — Brief

Fetch the full issue:

```
gh issue view N --comments --json number,title,body,labels,comments,createdAt,author
```

Find the agent brief comment — it will contain the heading `## Agent Brief`. This is the contract.

Extract:
- **Category** (`bug` or `enhancement`)
- **Summary** — one-line description of the goal
- **Current behavior** — what the system does now
- **Desired behavior** — what it should do after
- **Key interfaces** — types, functions, config shapes to look for or modify
- **Acceptance criteria** — the checklist; these are your definition of done
- **Out of scope** — do not touch these

If no agent brief comment exists, use the issue body. Flag this to the maintainer: brief-less issues are harder to implement correctly.

## Phase 3 — Explore

Use the key interfaces from the brief to orient codebase exploration. Do not read everything — find the seam.

For each key interface named in the brief:
1. `grep` for the type/function name to locate the relevant files
2. Read the implementation and callers
3. Understand what would need to change to reach the desired behavior

For large codebases (>20 relevant files), spawn an exploration sub-agent:

```
Agent(
  prompt = "Explore the codebase for: <summary>. Key interfaces: <list>. Return: affected files, relevant types/functions, your understanding of what needs to change.",
  subagent_type = "Explore"
)
```

Do not start implementing until exploration is complete.

## Phase 4 — Plan

Before writing code, map each acceptance criterion to a concrete implementation step. State the plan in one short paragraph or bullet list — this is for your own orientation, not a user-facing document. Identify any risks or ambiguities and surface them to the maintainer now, before making changes.

If the brief is under-specified for any criterion, ask one targeted question. Do not ask more than needed — if you can make a reasonable judgment call, make it and document it in the PR body.

## Phase 5 — Implement

### Branch

Create a branch before touching any files:

```
git checkout -b fix/issue-N-short-title    # for bugs
git checkout -b feat/issue-N-short-title   # for enhancements
```

Never commit directly to main.

### Write the code

- Implement what the brief's **desired behavior** describes
- Respect the **out of scope** list — do not touch adjacent things
- Follow the project's existing conventions (formatting, naming, test style)
- Run the project's type checker and linter as you go; fix errors immediately

### Tests

If the brief is a bug fix and a correct seam exists — write a failing test first, then fix it (red-green). If it is an enhancement, write tests that verify the new behavior described in the acceptance criteria.

If no correct seam exists, document the gap in the PR body.

### Verification loop

After implementing, work through the acceptance criteria checklist one by one. For each:
- State what you did to satisfy it
- Run the relevant command or test to confirm it passes
- If it fails, fix before proceeding

Do not open a PR until all acceptance criteria are met.

## Phase 6 — Ship

```
git add <specific files>
git commit -m "<type>: <summary from brief>"
git push -u origin <branch>
gh pr create \
  --title "<summary from brief>" \
  --body "$(cat <<'EOF'
## Summary
<one-paragraph description of what changed and why>

## Acceptance criteria
- [x] criterion 1
- [x] criterion 2

## Notes
<any judgment calls made, gaps documented, or out-of-scope items noticed>

Closes #N
EOF
)"
```

Return the PR URL to the maintainer.

## Phase 7 — Handoff

After the PR is open, remove the `ready-for-agent` label from the issue — it is now in-flight, not queued:

```
gh issue edit N --remove-label ready-for-agent
```

Do not close the issue — the PR's `Closes #N` will close it automatically on merge.

## Key Invariants

- NEVER implement from the issue body alone — find the agent brief comment first
- NEVER commit directly to main or master
- NEVER open a PR before all acceptance criteria are verified
- NEVER touch anything listed under **Out of scope**
- ALWAYS include `Closes #N` in the PR body
- ALWAYS remove `ready-for-agent` from the issue when the PR is open
- ALWAYS run type checker and linter before pushing — fix errors, never suppress
- ALWAYS surface ambiguities in Phase 4, not mid-implementation

## Vocabulary

**User says (route here):**
- "pick up an issue", "work on a ready-for-agent issue", "/implement"
- "implement issue #N", "fix issue #N", "action issue #N"
- "start work on #N", "take on #N", "pick up #N"
- "what's ready for me to work on?"

**Does NOT handle:**
- Triaging or classifying issues → `/triage`
- Diagnosing hard bugs before they reach `ready-for-agent` → `/diagnose`
- Writing agent briefs → `/triage` (produces the brief as part of moving to `ready-for-agent`)
- Reviewing the PR after it's open → `/review`
- Shipping unrelated local changes → `/ship`
