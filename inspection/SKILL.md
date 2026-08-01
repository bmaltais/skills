---
name: inspection
description: Formal technical inspection of a change — perspective reviewers find defects, tests confirm them, a record tracks rework.
disable-model-invocation: true
---

An **inspection** is a defect hunt, not a redesign. Reviewers record what is wrong; the author decides how to fix it. Every defect that leaves this skill is one a third party can check — a failing command, or a line someone else can point at.

## The product

An **inspection record** at `.claude/inspections/<slug>.md`, handed to the author as the rework list and re-read at follow-up.

- **Composition** — a header (base ref, files, line count), then one entry per defect: `file:line`, the perspective that raised it, a one-sentence claim, and a failure scenario (inputs → wrong result). Then a verification block: the exact commands run and their exit status.
- **Derivation** — the diff against the base ref, plus the repo's checklist. Missing base ref or unrunnable tests: halt and say which.
- **Quality criteria** — every entry anchors to a line in the diff; every entry states a consequence, not a preference; the verification block names commands, not intentions.

## Preconditions

```bash
git rev-parse --verify <base>          # base ref resolves
git diff --stat <base>...HEAD          # diff is non-empty
```

Halt if either fails. If the diff exceeds ~400 changed lines, split it into batches by subsystem and inspect each separately — review accuracy falls off a cliff past that, and one record per batch keeps entries anchored.

## Roles

You are the **moderator**: you scope the batch, dispatch reviewers, and own the record. Reviewers are subagents. Each is given the diff, one perspective, and its own output file — `/tmp/inspection-<perspective>.md` — so parallel writes never collide. You are the only writer of the record itself.

## Perspectives

Dispatch these in parallel, one agent each, at the tier named. The tier is the cheapest model that can pass this perspective's done-check — a reviewer that only enumerates and reports runs on haiku; one that weighs design runs on sonnet. Your own model is irrelevant to the choice.

| Perspective | Tier | Looks for |
|---|---|---|
| Maintenance programmer | sonnet | The person changing this in a year: leaked implementation detail across a module boundary, a class given a second reason to change, a new dependency that could have been an argument. |
| End user | sonnet | What breaks in their hands: unhandled input, a silent failure, a message that explains nothing, a behaviour change nobody asked for. |
| Regression hunter | haiku | What existing behaviour this alters: every caller of every changed signature, defaults that shifted, state now written from two places. |
| Test auditor | haiku | Whether the change is pinned: which new branch has no test, which test passes without asserting, which failure is reported by hand rather than by a red run. |

## The reviewer brief

A reviewer sees none of this conversation, and the cheaper the tier the less it infers. Give every reviewer all of:

- the base ref and the exact command to read the diff — `git diff <base>...HEAD -- <paths>`
- its perspective row, verbatim, and `.claude/inspection-checklist.md` if it exists
- its own output path, `/tmp/inspection-<perspective>.md`
- the entry format, verbatim: ``- `path/to/file.py:42` — <one-sentence claim> — <inputs → wrong result>``
- the return shape: that file, defects only, an empty file when it finds none

For the haiku pair, name the searches rather than the goal — a mechanical tier does what it is told and infers nothing. Regression hunter: `grep -rn` for each changed symbol across the repo, one entry per caller the diff leaves stale. Test auditor: list changed functions, then the test files naming each; a function no test names is an entry.

A reviewer that returns prose instead of the entry format has a brief defect: fix the brief and re-dispatch at the same tier. Escalate a tier only after a second failure on a brief you believe in. Full routing rules: `/delegate`.

## Verify

Reviewer claims are candidates, whatever tier raised them. Open each entry's `file:line` in the diff yourself and confirm the claim describes what is there; an entry you cannot anchor is dropped. Then run the repo's own gates and record exit status:

```bash
<test command>          # full regression suite, not the new tests alone
<type-check command>    # e.g. npx tsc --noEmit
<lint command>          # e.g. npx eslint . --quiet
```

A claim contradicted by a green suite either names an untested path — record it as a test-coverage defect — or dies. Drop it from the record and say so.

## Record and follow up

Write the record. Then, when the author reports rework done, re-run the verify block and check each entry against the new diff: fixed, or still open with the line it now sits at. An entry closed without a re-run stays open.

Defects that recur across inspections belong in `.claude/inspection-checklist.md` — one line each, phrased as a question a reviewer answers while reading ("Are business rules isolated from transport code?"). This file is the repo's memory of where it goes wrong; load it into every reviewer.

## Postconditions

```bash
test -s .claude/inspections/<slug>.md                      # record exists and is non-empty
grep -cE '^- `[^`]+:[0-9]+`' .claude/inspections/<slug>.md # every defect carries file:line
```

The verify commands above must all have been run, with exit status recorded, before the record is handed over.
