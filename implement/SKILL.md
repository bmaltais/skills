---
name: implement
description: "Implement a piece of work from a spec, tickets, or an agent brief — the middle step of triage → implement → review."
disable-model-invocation: true
---

Implement the work described in the spec, tickets, or **agent brief**, and hand `/review` something it can check against that brief.

**Product** — commits on a branch, plus a PR that links the issue so review reads the brief and the diff together. Every acceptance criterion traces to a commit or to a test that exercises it, and the files touched stay inside the brief's stated scope.

## Before starting

The acceptance criteria are in front of you. Where the spec has none, write them and get them agreed before touching code — an implementation with no agreed bar gets reviewed against opinion.

`git status` is clean, and HEAD is on a branch other than the default. Branch first if it is not.

Name the repo's three check commands now:

```bash
python3 ~/.claude/skills/implement/scripts/detect_checks.py .
```

It prints **typecheck**, **single-file test**, and **full suite**, which the rest of this skill refers to by those names. Substitute the real path for a `<file>` placeholder when you run one.

A `MISSING` line, or exit 1 on a repo it does not recognise, means you name that command yourself — from the CI config or by asking — and say out loud which one you had to supply. An unnamed check is one you will skip without noticing.

## Implement

Use `/test-driven-development` at the seams agreed in the brief.

Work one acceptance criterion at a time, and finish it — the criteria after it are still there when you return. A criterion is done when a test fails without your change and passes with it, and typecheck plus that single-file test are green.

## Close

Run the full suite once, in full, and read the output.

Then `/code-review`, and address what it raises.

Then commit and open the PR with `Closes #N` for each linked issue, so review inherits the brief.

**Done when** the full suite exits 0, every acceptance criterion maps to a commit or a test, and the PR links its issue. A criterion you chose to leave out is named in the PR body as out of scope, with the reason.
