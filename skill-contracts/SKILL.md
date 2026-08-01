---
name: skill-contracts
description: Reference for authoring a skill — the contract it owes, plus the bundled writing-great-skills reference.
disable-model-invocation: true
---

Two halves of authoring a skill. This file is the **contract** — what the skill owes. How its text is written (context load, information hierarchy, leading words, pruning, failure modes) is the other half: read [`references/writing-great-skills.md`](references/writing-great-skills.md) in full before writing or editing any SKILL.md, and [`references/GLOSSARY.md`](references/GLOSSARY.md) for term definitions.

A skill is a promise that the same process runs every time. A **contract** is the part of that promise a third party can check. Anything the agent grades by its own judgment isn't in the contract.

## The product

Name the artifact the skill exists to hand back, once, near the top. Four things, in a sentence or a short list — not a template to fill in:

- **Purpose** — what the reader or the next skill does with it.
- **Composition** — its parts. A review returns findings; a finding has a file, a line, a claim.
- **Derivation** — what it's built from, so a run with the inputs missing halts instead of inventing them.
- **Quality criteria** — the properties that make it acceptable, phrased so someone other than the author can apply them.

Skills that only steer behaviour (a mode, a stance, a review lens) own no artifact and skip this. A skill that produces a file, a report, or a structured result and never says what it consists of gets a different shape every run — the failure the contract exists to stop.

## Preconditions

State what must already be true for the skill to work: the tool installed, the repo clean, the branch pushed, the input file present. Check the cheap ones with a command the agent actually runs, and halt on failure — an unmet precondition silently absorbed produces a plausible artifact built on nothing, which costs more than stopping.

Keep the list to conditions that genuinely break the run. Every one you add is load, and one the agent would notice anyway is a no-op.

## Postconditions

A completion criterion the agent grades itself is a preference. A **postcondition** is a criterion something else grades:

1. **A command that exits nonzero** — the test suite, the type-checker, the linter, a script the skill ships beside itself. Strongest, because it cannot be reasoned around and stays true as the skill ages.
2. **A structural check on the artifact** — the file exists, the JSON parses against a schema, every finding carries a line number. Cheap, and catches the shapeless-output failure directly.
3. **A named reviewer** — a subagent given the quality criteria and no knowledge of how the work was done.

Reach for the highest rung the work supports. Prose criteria are the floor, not a tier: they steer the run, they don't close it.

Write the postcondition where the step ends, and give it the exact command. "Run the tests" is a preference; `npm test -- --run` is a postcondition.

This skill's own postcondition, run on the skill you just wrote or edited:

```bash
python3 ~/.claude/skills/skill-contracts/scripts/check_skill.py <skill-dir>
```

It checks what a third party can check — frontmatter parses, `name` matches the directory, the description suits the invocation mode, every relative link resolves — and warns on sprawl and **negation**. Exit 0 closes the edit; errors are the contract failing, warnings are for your judgment.

## Prefer the script

A skill written in prose is re-interpreted every run; a script beside it runs the same way forever. When part of a procedure is fully determined — a fixed command sequence, a file transform, a formatting pass — ship it as a script in the skill folder and have the skill invoke it. Keep prose for the parts that need judgment.

This is the cheapest predictability available, and the parts of a skill that most need it are exactly the parts easiest to move out.

## Races

Skills that fan out to parallel agents inherit real race conditions: two agents editing one file, both reading state the other is mid-write, an ordering the skill assumed and never enforced.

Give each parallel agent its own file to write, and merge after the barrier. Where they must share, name the one agent that owns the write. A skill that dispatches N agents at one target without saying who writes produces a different result depending on which finished first — the same class of bug, arriving through a workflow instead of a thread.

Worktree isolation is the heavy version; use it when agents mutate a shared tree and separate output files aren't enough.
