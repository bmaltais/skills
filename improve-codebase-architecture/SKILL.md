---
name: improve-codebase-architecture
description: Find deepening opportunities in a codebase, informed by the domain language in CONTEXT.md and the decisions in docs/adr/. Use when the user wants to improve architecture, find refactoring opportunities, consolidate tightly-coupled modules, or make a codebase more testable and AI-navigable.
categories: [software-development]
agents: [pi, hermes, claude, copilot]
metadata:
  source: custom
  scope: global
---

# Improve Codebase Architecture

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones. The aim is testability and AI-navigability.

## Glossary

Use these terms exactly in every suggestion. Consistent language is the point — don't drift into "component," "service," "API," or "boundary." Full definitions in [LANGUAGE.md](LANGUAGE.md).

- **Module** — anything with an interface and an implementation (function, class, package, slice).
- **Interface** — everything a caller must know to use the module: types, invariants, error modes, ordering, config. Not just the type signature.
- **Implementation** — the code inside.
- **Depth** — leverage at the interface: a lot of behaviour behind a small interface. **Deep** = high leverage. **Shallow** = interface nearly as complex as the implementation.
- **Seam** — where an interface lives; a place behaviour can be altered without editing in place. (Use this, not "boundary.")
- **Adapter** — a concrete thing satisfying an interface at a seam.
- **Leverage** — what callers get from depth.
- **Locality** — what maintainers get from depth: change, bugs, knowledge concentrated in one place.

Key principles (see [LANGUAGE.md](LANGUAGE.md) for the full list):

- **Deletion test**: imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep.
- **The interface is the test surface.**
- **One adapter = hypothetical seam. Two adapters = real seam.**

This skill is _informed_ by the project's domain model. The domain language gives names to good seams; ADRs record decisions the skill should not re-litigate.

## Process

### 0. Repo health check

Before exploring architecture, run:

```
git status
git rebase --show-current-patch   (exit code 0 only if rebase is in progress)
```

If the repo is in a **broken state** (interrupted rebase, unresolved conflicts, stash pile-up), surface it as a **`#0` blocking item** before any architectural candidates. Explain the state and offer to fix it first. Do not proceed with architecture analysis until the repo is clean — broken state masks real friction.

Example blocking item:
> **#0 (blocking) — Interrupted rebase in progress**
> `git status` shows "interactive rebase in progress". The last `git pull --rebase` was interrupted and never finished. Other machines cannot receive pushes until this is resolved. Recommend fixing before proceeding.

### 1. Explore

Read the project's domain glossary and any ADRs in the area you're touching first.

Then use the Agent tool with `subagent_type=Explore` to walk the codebase. Don't follow rigid heuristics — explore organically and note where you experience friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow** — interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they're called (no **locality**)?
- Where do tightly-coupled modules leak across their seams?
- Which parts of the codebase are untested, or hard to test through their current interface?

Apply the **deletion test** to anything you suspect is shallow: would deleting it concentrate complexity, or just move it? A "yes, concentrates" is the signal you want.

### 2. Present candidates

Present a numbered list of deepening opportunities. For each candidate:

- **Files** — which files/modules are involved
- **Problem** — why the current architecture is causing friction
- **Solution** — plain English description of what would change
- **Benefits** — explained in terms of locality and leverage, and also in how tests would improve

**Use CONTEXT.md vocabulary for the domain, and [LANGUAGE.md](LANGUAGE.md) vocabulary for the architecture.** If `CONTEXT.md` defines "Order," talk about "the Order intake module" — not "the FooBarHandler," and not "the Order service."

- **ADR conflicts**: if a candidate contradicts an existing ADR, only surface it when the friction is real enough to warrant revisiting the ADR. Mark it clearly (e.g. _"contradicts ADR-0007 — but worth reopening because…"_). Don't list every theoretical refactor an ADR forbids.

Do NOT propose interfaces yet. Ask the user: "Which of these would you like to explore?"

### Example: Decomposing a monolithic linter

A common deepening opportunity is a large file that bundles many independent checks (e.g. `lint.py` at 439 lines). The pattern:

1. Identify the independent concerns (file naming, frontmatter, tags, headings, links, orphans, etc.)
2. Create a `rules/` package with each concern as a module
3. Define a thin `Rule` interface (`name: str`, `run(path, page, ...) -> list[str]`)
4. Provide a `run_all()` helper that iterates rules and collects results
5. Rewrite the orchestrator (`lint.py`) to be thin — just a loop calling `run_all()`

Result: each rule is independently testable, adding a new check is just adding a file, and the interface is tiny. See [references/linter-decomposition.md](references/linter-decomposition.md) for the full walkthrough.

### 3. Grilling loop

Once the user picks a candidate, drop into a grilling conversation. Walk the design tree with them — constraints, dependencies, the shape of the deepened module, what sits behind the seam, what tests survive.

Side effects happen inline as decisions crystallize:

- **Naming a deepened module after a concept not in `CONTEXT.md`?** Add the term to `CONTEXT.md` — same discipline as `/grill-with-docs` (see [CONTEXT-FORMAT.md](../grill-with-docs/CONTEXT-FORMAT.md)). Create the file lazily if it doesn't exist.
- **Sharpening a fuzzy term during the conversation?** Update `CONTEXT.md` right there.
- **User rejects the candidate with a load-bearing reason?** Offer an ADR, framed as: _"Want me to record this as an ADR so future architecture reviews don't re-suggest it?"_ Only offer when the reason would actually be needed by a future explorer to avoid re-suggesting the same thing — skip ephemeral reasons ("not worth it right now") and self-evident ones. See [ADR-FORMAT.md](../grill-with-docs/ADR-FORMAT.md).
- **Want to explore alternative interfaces for the deepened module?** See [INTERFACE-DESIGN.md](INTERFACE-DESIGN.md).

### 4. Implementation

When the user approves one or more candidates (including "fix them all"):

1. **Write the plan first** — post a numbered list of concrete file operations (create X, edit Y, delete Z) before touching any file. Keep it short: one line per step.
2. **Get implicit or explicit buy-in** — if the user says "do it" or "fix them all", proceed immediately without asking again. Only pause if the plan involves deleting files or breaking public interfaces.
3. **Execute step by step** — complete each step, mark it done, move to the next.
4. **Validate at the end** — run a syntax check (or equivalent) on every modified file and report results. Do not skip this.

**Do not narrate while thinking.** Write the plan, then act. Avoid "I will now…" preamble between steps.