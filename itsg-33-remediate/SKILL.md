---
name: itsg-33-remediate
description: >-
  Work open ITSG-33 gap issues one at a time under a TDD discipline, delivering
  each fix as a branch and draft PR. Use when the user wants to remediate PBMM
  control gaps (itsg-33:gap issues) produced by itsg-33-assess.
---

Work through the open gaps produced by `itsg-33-assess`, highest severity first,
one at a time. Every fix follows the same discipline: capture a test baseline,
propose the fix, apply it on its own branch, verify tests are green, then open a
self-contained draft PR. Never touch `main` directly, and never move to the next
gap without the user's explicit go-ahead.

### Step 1 — Load gap issues

Read `security/itsg33.yaml` to determine tracker mode.

**GitHub mode** (`tracker: github`):
```bash
bash skills/itsg-33-remediate/scripts/gh-list-tagged-issues.sh itsg-33:gap
```

**Azure DevOps mode** (`tracker: azure-devops`):
```bash
bash skills/itsg-33-remediate/scripts/ado-list-tagged-items.sh "<ado_org>" "<ado_project>" itsg-33:gap
```
For each returned `id`, fetch full field values:
```bash
az boards work-item show --id <id> --org "<ado_org>" -o json
```
Control ID/name are parsed from the title (`[itsg-33:gap] <Control ID> — <Control Name>` — the
same format `itsg-33-assess` used to create it). Source reference is the work item ID/URL
(`<ado_org>/<ado_project>/_workitems/edit/<id>`).

**Local mode** (`tracker: local`):
Read every file in `security/gaps/`, **excluding** files ending in
`-needs-test.md` — those are tasks created by a prior Step 4, not gaps.

For every open gap (any mode), also read its linked evidence card,
`security/evidence/<control-id>.md`. The evidence card — not the gap issue, work item, or gap
file — is the source of truth for **Severity**, since `evidence-card.md`'s
`**Severity:** <P1 | P2 | P3>` header field is the only place severity is
recorded in a form every tracker mode can read the same way (GitHub conveys it only via issue
label and Azure DevOps only via a tag, neither of which local mode has an equivalent of).

Build one record per gap with: control ID, control name, severity, finding,
confidence note, recommended action, evidence card path, and a source
reference (issue number, work item ID, or gap file path). Completion: every open gap
(possibly zero) is loaded into this common shape. If there are zero open gaps,
report "no open ITSG-33 gaps found" and stop — do not proceed to Step 2.

### Step 2 — Sort gaps

Order the queue: **P1** first, then **P2**, then **P3**; within the same
severity, alphabetically by control ID. Completion: a single ordered queue of
gap records.

### Step 3 — Present next gap

Show the user the first gap in the queue: control ID + name, finding,
confidence note, and recommended action (from the evidence card). This is
informational — proceed directly to Step 4 with no approval gate here; the
gate the user actually needs is at Step 5, before anything is written.
Completion: the gap's details have been shown to the user.

### Step 4 — Test baseline

Auto-detect the repo's test runner:

| Signal | Command |
|--------|---------|
| `package.json` | `npm test` |
| `go.mod` | `go test ./...` |
| `pytest.ini`, `setup.py`, or `pyproject.toml` | `pytest` |
| `Makefile` with a `test` target | `make test` |

**If a runner is found:** run it and record the pass/fail baseline (exit code
plus counts, however the runner reports them). This baseline is what Step 7
must match or beat, and what Step 8's PR body cites as the "before" result.

**If no runner is found:** stop — do not propose or apply a fix for this gap.
Create a needs-test task instead:

- GitHub mode:
  ```bash
  bash skills/itsg-33-remediate/scripts/gh-create-issue.sh \
    "[itsg-33:needs-test] <control-id> — write failing test" \
    itsg-33:needs-test \
    <body-file>
  ```
  where `<body-file>` explains the gap needs a test that fails against the current code before
  `itsg-33-remediate` can touch it.
- Azure DevOps mode:
  ```bash
  bash skills/itsg-33-remediate/scripts/ado-create-work-item.sh \
    "<ado_org>" "<ado_project>" Issue \
    "[itsg-33:needs-test] <control-id> — write failing test" \
    itsg-33:needs-test \
    <description-file>
  ```
  with the same explanation, written as simple HTML.
- Local mode: write `security/gaps/<control-id>-needs-test.md` with the same
  content.

Then go straight to Step 10's continue-or-stop gate for this gap (skip Steps
5-9 entirely) — creating the task pauses work on *this* gap, it does not end
the whole run, so the user still decides whether to move on to the next queued
gap or stop here.

Completion: either a captured pass/fail baseline, or a needs-test task created
and the Step 10 gate reached.

### Step 5 — Propose fix

Describe the specific code or IaC change that would satisfy the control —
concrete enough that the user knows exactly what's about to be written (which
files, which resource blocks, which lines). Show this to the user and wait for
explicit approval before doing anything to the working tree. If the user wants
changes, revise the proposal and ask again. If the user wants to skip this gap
entirely, go to Step 10's gate without applying anything. Completion: the user
has explicitly approved a specific proposed change (or chosen to skip this
gap) — an unanswered proposal is not completion.

### Step 6 — Apply fix on branch

Create branch `itsg33/fix/<control-id>` from the current `HEAD`. If that branch
already exists, stop and ask the user how to proceed (reuse it, delete it, or
pick a different name) — never silently overwrite or force-delete an existing
branch. Apply the approved fix on this branch. Completion: the branch exists
and contains the approved fix, committed.

### Step 7 — Verify green

Re-run the exact command captured in Step 4. It must pass. If it doesn't,
return to Step 5 to revise the fix — do not open a PR against red tests. If it
still isn't green after two revision attempts, stop and tell the user; leave
the branch and its commits in place for manual follow-up rather than
discarding them. Completion: the Step 4 command exits clean on this branch.

### Step 8 — Open draft PR

First, check whether a usable remote exists (the same check `itsg-33-assess` Step 1
uses to detect tracker mode):

```bash
git remote -v
```

**If no remote exists (`tracker: local`):** stop here — do not attempt to open a PR (there is
nothing to open one against). Tell the user: the fix is committed on branch
`itsg33/fix/<control-id>` with tests green, but no draft PR was opened because this repo has no
remote; push a remote and re-invoke this step (or open the PR manually) once one exists.
Completion (no-remote case): the branch and its green commit exist; the user has been told why no
PR was opened.

**If a remote exists:** proceed as below. Title: `fix(<control-id>): <control name> — <one-line summary>`.

Body (fully self-contained — the reviewer should need nothing else open):

```
## Control
<Control ID> — <Control Name> (PBMM <severity>)

## Finding
<finding + confidence note, from the evidence card>

## Fix
<rationale for the change just made>

## Test Results
**Before:** <Step 4 baseline>
**After:** <Step 7 result>

<closing line — see below>
```

The closing line depends on tracker mode:
- GitHub mode: `Closes #<gap-issue-number>`
- Azure DevOps mode: none — the PR is linked to the work item directly by the script (see
  below), not via a body keyword.
- Local mode: `Resolves local gap: security/gaps/<control-id>.md` — since
  there's no merge-triggered auto-close in local mode, follow it with a line
  asking the user to delete that file once this PR merges.

**GitHub mode:**
```bash
bash skills/itsg-33-remediate/scripts/gh-create-pr.sh "<title>" <body-file> <gap-issue-number>
```
The script appends the `Closes #<N>` line to the body itself.

**Azure DevOps mode:**
```bash
bash skills/itsg-33-remediate/scripts/ado-create-pr.sh \
  "<ado_org>" "<ado_project>" "<ado_repo>" \
  "<source-branch>" "<title>" <body-file> <work-item-id>
```
Target branch is omitted — the script auto-detects the repo's default branch. The script's
`az repos pr create --work-items` call links the gap work item in the same invocation; there is
no separate linking step. **Known limitation:** this links the PR to the work item but does not
by itself close the work item on merge — whether it auto-transitions depends on the org's own
branch-policy/completion settings, outside this skill's scope since it only ever creates a draft
PR. Treat this the same as local mode's manual-cleanup posture, not GitHub mode's automatic
`Closes #N` behavior.

**Local mode:** no script — there is nothing to open a PR against (handled by the no-remote
branch above).

Completion: a draft PR exists with the correct title format and every body
field populated (no field left as a placeholder).

### Step 9 — Update POA&M

**If Step 8 opened a PR:** edit `security/evidence/<control-id>.md`'s header block to add or
update a `**Remediation Ticket:** <PR URL>` line, alongside its existing `Severity` and
`Finding` fields. The evidence card is the artifact meant to persist into the SAR package, so
it — not the gap issue or gap file, which close or get deleted — is where this link needs to
survive.

For local tracker mode only, also add or update the same
`**Remediation Ticket:** <PR URL>` line in the still-open gap file, so the
team can see the link while that file still exists, ahead of its manual
deletion after merge.

Known limitation: this link is best-effort, not durable. A future
`itsg-33-assess` re-assessment of this control (a cache miss) regenerates the
evidence card from a template with no `Remediation Ticket` field, silently
dropping it — and `assessment-report.md`'s POA&M table never carries it
either, since it's generated from `assessment-state.yaml`, which also lacks
the field. Rely on the merged PR (and, in GitHub mode, the closed gap issue)
as the authoritative record; closing this regeneration gap belongs to a
future `itsg-33-assess` change, not this skill.

**If Step 8 stopped because there was no remote:** skip this step entirely — there is no PR URL
to record yet. Proceed directly to Step 10.

Completion: either the evidence card's (and, in local mode, the gap file's) `Remediation
Ticket` field is set to the PR URL, or Step 8 had no remote and this step was skipped.

### Step 10 — Continue or stop

Ask the user: move on to the next gap in the queue, or stop here. Reached from
the end of a completed fix (Step 9), from Step 4's needs-test path, and from a
skipped gap in Step 5 — in every case, the next gap only starts on explicit
user go-ahead. The skill never auto-chains through the queue on its own.
Completion: the user has chosen to continue (loop to Step 3 for the next
queued gap) or to stop (end the run here).
