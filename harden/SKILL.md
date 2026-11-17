---
name: harden
description: Turn a repeated agent mistake into a repo constraint. Use when the user corrects you on something fixable by code or config, when you see the same mistake twice, or when a bad pattern is spreading through a codebase.
---

The codebase is the agent's memory: agents extend whatever pattern they find, so a workaround left in place gets copied until it is the house style. Every correction is a **leak**. Plug it where it stops the most agents, not just this one.

## Plug the leak

1. Name the mistake as a pattern, not an instance ("raw `fetch` in components", not "this file").
2. Take the highest rung that closes it, top down:
   1. **Unrepresentable**: change the structure (types, module boundaries, data shape, one blessed helper) so the mistake cannot be written. Enforce boundaries through the import graph.
   2. **Lint rule, type check or CI step**: red on the bad pattern. When the cleanup is too big for now, write the rule first to stop the bleeding.
   3. **Guidance**: `AGENTS.md` line, skill, review-bot rule. An agent can still skip it; use it for what rungs 1–2 cannot express.
   4. **Style guide, human review**: last resort; it relies on a person catching it in every diff.
3. Check the leak is plugged: reintroduce the mistake and see the chosen rung go red (or, for rung 3, name where the agent will read it).

Weigh rung 1 against its cost to humans: a locked-down codebase is annoying to hand-write and ideal for agents. Say which trade you picked.

## Keep the garden

- One **paved path** per common task; delete the competing ways instead of documenting them.
- Delete the existing instances of the pattern you just banned, so the next agent copies clean code. Fix the problem rather than commenting a workaround: agents copy a commented hack as its own justification.
- Leave the repo in a state you would be glad to see copied.

## Verification gaps

When you could not check your own work because you could not run the app, build a **verification skill** in the repo's skill directory:

- A CLI that runs the app and collects evidence (traces, snapshots, screenshots), reproducible across sessions rather than a fresh script each time.
- A **feature map**: the app's features, how a user reaches each (shortcut, element, route), and what each does, so a vague bug report resolves to a concrete place. Keep it current with an automation.

Evidence, not the agent's say-so, is what earns trust.

Source: Lauren Tan (poteto), "here's how i shipped 2,500 PRs last month to production", https://www.youtube.com/watch?v=Z-jNqqIYGm4
