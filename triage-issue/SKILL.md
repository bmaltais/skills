---
name: triage-issue
description: see description.md
user-invocable: true
argument-hint: "<symptom description or paste error>"
---

# triage-issue

Turns a one-line bug report into a fully structured GitHub issue with root cause,
classification, and TDD fix plan. Creates the issue immediately — no "shall I?" gate.

## Routing Table

| Knowledge area | Load |
|---|---|
| Bug classification criteria and git detection commands | `references/bug-classification.md` |
| GitHub issue format, section specs, `gh` CLI example | `references/triage-issue-template.md` |

## Workflow

```
FUNC triage(report: str) -> GitHubIssue:

  # 1. CAPTURE — collect enough signal to explore
  IF report is vague:
    ask(QUESTIONS, max=3)          # symptom, reproduction steps, environment
    WAIT for answers before proceeding

  # 2. EXPLORE — spawn sub-agent; do not proceed until it returns
  exploration = Agent(
    prompt = """
      Your skill definition is at:
      skills/engineering/skills/triage-issue/SKILL.md
      Read it, then investigate the bug:

      Symptom: {report}

      Tasks:
      1. Trace the relevant code paths — follow call chains to the failure point
      2. Read error handling around the failure
      3. Run `git log --follow -p -- <file>` on involved files
      4. Run `git log --grep="<keyword>"` for related commits
      5. Run `git bisect` if regression signals present
      6. Return: affected files, likely fault location, git evidence, your hypothesis
    """,
    subagent_type = "general-purpose"
  )
  WAIT exploration.complete()      # INVARIANT: never classify before exploration returns

  # 3. CLASSIFY — load references/bug-classification.md
  classification = classify(exploration.result)   # regression | missing-feature | design-flaw

  # 4. TDD PLAN — design ≥2 RED-GREEN cycles
  tdd_plan = design_tdd_cycles(classification, exploration.result)
  ASSERT len(tdd_plan) >= 2        # INVARIANT: minimum two cycles

  # 5. ACCEPTANCE CRITERIA — one criterion per cycle's final GREEN state
  criteria = [cycle.green_state for cycle in tdd_plan]

  # 6. CREATE ISSUE — immediately, no confirmation prompt
  gh issue create \
    --title "[BUG] {concise_title}" \
    --body  render(template=references/triage-issue-template.md, data={...})
  # INVARIANT: never ask "shall I create the issue?" — just create it

  RETURN issue_url
```

## Vocabulary

**User says (route here):**
- "triage this bug", "triage-issue", "/triage-issue"
- "investigate this issue", "diagnose this error", "root cause this"
- "create a bug issue", "write up this bug", "make a GitHub issue for this bug"
- "what's causing this error", "file a bug for"

**Does NOT handle:**
- Fixing the bug or writing implementation code → `tdd` skill
- General GitHub issue management (not bugs) → use `gh` CLI directly
- Feature requests without a defect → standard issue creation
- Modifying source files during triage (read-only exploration only)
- Creating the issue before the exploration sub-agent completes

## Key Invariants

- NEVER create the GitHub issue before the exploration sub-agent returns
- NEVER modify source files — triage is strictly read-only (git log, grep, read)
- NEVER ask for user approval before creating the issue — create it immediately
- NEVER produce a TDD plan with fewer than 2 RED-GREEN cycles
- ALWAYS label evidence as [EXTRACTED: git/code ref] or [INFERRED: reasoning] in the issue body
- ALWAYS state uncertainty explicitly when confidence is low — a vague root cause beats a confident wrong one
- ALWAYS spawn exploration as a separate sub-agent for context isolation
