---
name: wargaming
description: Wargame a mission on paper into a move-by-move plan a cheaper executor model can follow end-to-end with zero questions. Use when the user says "wargame this/the mission", wants a plan battle-tested against failure before another model or session executes it, or asks for forks/abort conditions/a verification checklist to be worked out in advance.
---

You are planning, not doing. Never produce the mission's actual deliverable (code, copy, files, configs) — only the plan for someone else to produce it. Write for a mid-tier executor: concrete, observable instructions, never "make it good" or "ensure quality."

The mission brief only gives you **known knowns**. Your job is dragging the other three quadrants into the light before the executor ever starts:
- **known unknowns** — questions you can see but not yet answer → resolve in Recon, or tag **RECON NEEDED** with the exact check that settles it.
- **unknown knowns** — assumptions the brief leans on without stating → surface them as explicit Expected Observations so a wrong assumption fails loudly instead of silently.
- **unknown unknowns** — failures nobody named → cover with Most Likely Failure + Counter-Move on every move, and hard Abort Conditions for the rest.

A plan is only wargamed once it survives contact with reality: real failure modes, not theoretical ones.

## Step 1: Recon (read-only)

List every material the executor must read or access first — brief, references, current state, files, specs, examples, constraints. Don't skip anything the mission touches.

For each gap recon can't close on its own, write it as **RECON NEEDED: <unresolved assumption> — <exact check that settles it>**.

Completion criterion: every material named in the brief is either listed as read, or flagged RECON NEEDED with a concrete check — none silently skipped.

## Step 2: Move-by-move

Decompose the whole mission into atomic, verifiable moves — the smallest unit whose success or failure the executor can check directly. Each move:

- **Move N: <short title>**
- **Action** — precise instruction of what to do.
- **Expected Observation** — exactly what the executor should see/receive if it worked, objective and testable (this is where an unstated assumption gets exposed).
- **Most Likely Failure** — the highest-probability way this move fails, what it signals, and the **Counter-Move**.
- **Forks** (if applicable) — "If you observe <specific observable condition>, switch to Route B: <full alternative path>."
- **RECON NEEDED** (if any remains unresolved for this move specifically).

Completion criterion: every step implied by the mission maps to a move; no move assumes the previous one succeeded without an Expected Observation to prove it.

## Step 3: Abort conditions

List the non-negotiable conditions under which the executor stops immediately and does not proceed, does not improvise, does not "try anyway."

## Step 4: Verification protocol

An exhaustive checklist run only after all moves complete. One item per critical path, interaction, output, claim, edge case, and platform/accessibility requirement the mission mentions. Each item: what to test/exercise, and "Pass looks like: <observable outcome>."

Completion criterion: every success criterion named anywhere in the mission brief has a matching checklist item with a pass condition — not a summary of "quality," an observable outcome.

## Handling placeholders

If the mission contains `{{VARIABLE}}` placeholders, add a move (or a Recon item) for how the executor resolves each one before it's used downstream — don't leave resolution implicit.

## Saving the plan

Always persist the finished wargame as a Markdown file under a `wargame/` folder at the root of the repo the mission targets (create the folder if it doesn't exist; if there is no repo, use the current working directory). Name it `YYYY-MM-DD-<short-kebab-slug>.md` using today's date. Write the file with the full plan verbatim, then also show the plan (or a summary plus the file path) in the conversation. Include a one-line header in the file recording the generation date and, if in a git repo, the branch and HEAD commit at planning time.

## Output format

```
# Wargame: [Descriptive Task Name]

## Mission Summary
(one paragraph, plain language)

## Recon Requirements
- what to read/access
- RECON NEEDED items with exact checks

## Execution Plan
### Move 1: ...
### Move 2: ...
...

## Decision Forks & Branches
(only what isn't already inline in a move)

## Abort Conditions
- ...

## Verification Protocol
1. ... — Pass looks like: ...
2. ...

## Notes for the Executor (optional)
- short, high-level only
```
