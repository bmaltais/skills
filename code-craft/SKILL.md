---
name: code-craft
description: Construction discipline for code a human will maintain — deep modules, one home per fact, red-first tests, gates run before "done". Use when writing a new module, class, or non-trivial function, when refactoring, when the user asks for production-grade / clean / maintainable code, or when another skill needs the bar for what counts as finished code.
---

The imperative is **complexity**: the code you write today is read by someone who has forgotten it. Every choice below buys a smaller thing to hold in the head.

## What you hand back

A change, its tests, and the gate output. The change is acceptable when a reader who did not write it can name the responsibility of each unit you touched from its name and signature alone, and when [the gates](#gates) exit clean.

## Before writing

Name the complexity you are paying down, in one line — it decides the shape of everything after. Ousterhout's three symptoms, in order of how often they bite:

- **Change amplification** — one decision forces edits in many places. Cure: give the fact [one home](#one-home-per-fact).
- **Cognitive load** — a caller must hold implementation details to use the thing. Cure: make the module [deep](#deep-modules).
- **Unknown unknowns** — the caller cannot tell what they must know. The worst of the three, and the reason interfaces get documented at the point of use.

If none of the three applies, the work is small: write the obvious code and go to [gates](#gates).

## Deep modules

A module earns its existence by the ratio of what it hides to what it exposes. Deep: a wide implementation behind a narrow interface. Shallow: an interface nearly as large as the body it wraps — it adds a name to learn and hides nothing.

The test, applied to every unit you add: **if the signature plus its doc is about as long as the body, the unit is shallow.** Fold it into its caller.

Shallow shapes to fold on sight:

- A pass-through method that forwards its arguments unchanged.
- A layer whose types mirror the layer below it one-for-one.
- An interface with exactly one implementation and no second one in the diff.
- A config flag whose value never varies at runtime — inline the value.

Abstraction earns its place by the complexity it hides, never by the flexibility it might someday offer. Extension points are bought with a second real caller, not with a guess. When a second caller arrives, extend by adding a case rather than by editing the tested path.

Depth also comes from **removing the special case**: a default that makes the empty input ordinary, an error defined out of existence, a single code path where two nearly-identical ones stood. Deleting a branch beats documenting it.

## One home per fact

Every piece of knowledge — a constant, a validation rule, a wire format, an ordering assumption — lives in exactly one place. Duplication is what turns a one-line change into a hunt.

Copy-pasted *shape* is fine; copy-pasted *knowledge* is the defect. Two functions that happen to look alike but change for different reasons stay separate.

## Names and comments

Names carry the *what*. Precise and long beats short and enigmatic; when a name needs a comment to be understood, rename it instead. Reserve comments for the *why* — the constraint, the trade-off, the reason the obvious approach fails here — and for what the caller must know but cannot see from the signature (the unknown unknowns above).

Comments that paraphrase the line below them get deleted as you pass.

## Red first

Write the test before the code and **watch it fail**. The failure message is the deliverable of this step: run the test, see red, and confirm it fails for the reason you intended rather than a typo or an import error. A test that has never failed proves nothing.

Then the smallest code that passes, then refactor with the test green.

## Gates

State the verification plan before you change code, and run it before you report. Run:

```bash
bash ~/.claude/skills/code-craft/scripts/gates.sh
```

It detects the project's own type-checker, linter, formatter, and test command, runs each that exists, and prints what it ran.

- **exit 0** — all gates passed. The change is reportable.
- **exit 1** — a gate failed. Fix it and re-run; a failing gate is the whole result until it passes.
- **exit 3** — no automated gate exists in this project. Say so plainly in the report and give the manual check you ran instead.

Reporting a change as done without a clean gate run is the one failure this skill exists to prevent.

## Leaving the file

Boy Scout Rule, scoped to what you touched: the files in your diff come out cleaner than you found them — a dead import removed, a misleading name fixed, a duplicated constant given its home. Files outside the diff stay as they are; a drive-by refactor is its own change, with its own gate run.

If the change wanted a structural fix bigger than the task, make the small fix, ship it green, and say in one line what the structure still wants.
