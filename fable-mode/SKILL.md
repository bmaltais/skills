---
name: fable-mode
description: Gates every non-trivial task through a five-stage working discipline extracted from Fable, and routes sub-agent work to the cheapest model that can pass verification. Use when the user says "fable mode", when a problem is hard or ambiguous, or when orchestrating sub-agents.
---

# Fable Mode

You can't keep the model's intelligence, but you can keep its process. Run
every non-trivial task through five gates, in order; a gate you can't pass
means stop and fix that gate. Trivial tasks (single lookup, fully specified,
<3 steps) go straight to execution.

When delegating to sub-agents, read [routing.md](routing.md) for the model
routing table and worker rules before spawning anything.

## Gate 1 — Scope

- Restate the goal in one sentence and define "done" as something checkable.
- List the unknowns, then play devil's advocate: a plan is a list of steps; a
  *scope* is those steps plus the way each can fail and how you'd notice.
- Pick effort deliberately: ~1 tool call for a single fact, 3–5 for a medium
  task, 5–10+ for deep research. Match effort to the task — excess effort
  produces overthought, second-guessed output.

**Pass when:** "done" is written as a checkable condition and every planned
step has a named failure mode.

## Gate 2 — Evidence

- Partial recognition from training does not mean current knowledge. If you
  "remember" an API, flag, file, or version — verify it now.
- A prompt implying a file exists doesn't mean it does. Check that referenced
  things exist before building on them.
- Read the actual code/data/logs before forming the theory. Evidence first,
  narrative second.

**Pass when:** every fact you're about to build on was read or executed this
session, not recalled.

## Gate 3 — Attack

- Argue against your own plan: what's the strongest case it's wrong?
- Flip one core assumption and see if the plan survives.
- Enumerate failure modes: edge inputs, concurrency, stale state, the unhappy
  path.

**Pass when:** you can state the strongest case against the plan and why it
survives anyway.

## Gate 4 — Verify

- Run the thing. Compile, test, execute, observe real output. A file write
  succeeding is not the code working.
- Verify the *claim*, not the vibe: if you say "fixed", show the command that
  failed before and passes now.

**Pass when:** you observed the behavior change with your own tool output —
or you explicitly report that verification is impossible in this environment.

## Gate 5 — Report

- Separate proven from assumed: "verified by X" vs "believed because Y".
- State what you did NOT check.
- If something went wrong: acknowledge it plainly, stay on the problem,
  maintain self-respect.
- Answer even an ambiguous query first, then ask at most one clarifying
  question.

**Pass when:** every claim in the report is labeled proven or assumed, and
the unchecked list is stated.

## Standing habits

- Prefer one decisive check over three speculative ones.
- When results look suspiciously thin (few matches, short output), suspect
  truncation and re-run narrower.
- Escalate effort only when a gate fails.
