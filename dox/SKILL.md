---
name: dox
description: Follow and maintain the DOX AGENTS.md contract hierarchy in this repo. Use before editing any file — walk root-to-target AGENTS.md chain first — and after any meaningful change to code, docs, or skill structure — update the nearest owning AGENTS.md and its Child DOX Index.
---

DOX treats every AGENTS.md as a binding work contract for its subtree. A file or folder must stay understandable from its nearest AGENTS.md plus every parent above it — that's the whole contract; everything below operationalizes it.

## Before editing: walk the DOX chain

1. Read the root `AGENTS.md`.
2. List every file or folder you expect to touch.
3. For each target, walk root → target, reading every `AGENTS.md` on the path. Where a parent's Child DOX Index lists a child whose scope contains the target, descend into that child and keep walking from there.
4. Treat the nearest `AGENTS.md` as the local contract; parents hold repo-wide rules. On conflict, the nearer doc wins on local detail — but no child may weaken a parent rule.

Completion criterion: every `AGENTS.md` on every root-to-target path has been read *this session*. Don't rely on memory of a prior read — a change since then (yours or someone else's) may have moved the contract.

## After editing: do a DOX pass

Every meaningful change gets a DOX pass before the task counts as done. A change is meaningful if it touches: purpose, scope, or ownership; durable structure, contracts, workflows, or operating rules; required inputs, outputs, permissions, constraints, side effects, or artifacts; user preferences about behavior, process, organization, or quality; or any AGENTS.md creation, deletion, move, rename, or index content.

1. Update the closest owning `AGENTS.md` for each meaningful change.
2. Propagate: parent-level structure, ownership, workflow, or index changes update parent docs; child docs follow when a parent change alters their local rules.
3. Delete stale or contradictory text on sight — don't just append.
4. Refresh every Child DOX Index affected by a creation, deletion, move, or rename.
5. Run whatever verification the affected AGENTS.md defines, if any.

Completion criterion: every path touched this task has been re-checked against its DOX chain, and every affected index/parent/child doc reflects the change — or you can name which doc was intentionally left unchanged and why.

## Creating a child AGENTS.md

Create one when a folder becomes a durable boundary — its own purpose, rules, responsibilities, workflow, materials, or quality bar distinct from its parent.

Section order: Purpose, Ownership, Local Contracts, Work Guidance, Verification, Child DOX Index.

- **Work Guidance**: current project or user standards; leave empty if none exist yet.
- **Verification**: an existing check only; leave empty until one exists.
- **Child DOX Index**: table of this folder's own children and their scope, same form as the parent's.

## Style

- Concise, current, operational — document stable contracts, not diary entries.
- Broad rules live in parent docs; concrete detail lives in child docs. Don't duplicate a rule across files unless each scope genuinely needs its own version.
- Delete stale notes instead of narrating their history.
- Trim obvious statements, repeated rules, misplaced detail, and warnings for risks that no longer apply.

## User preferences

Record durable behavior changes the user requests in the nearest AGENTS.md — root `AGENTS.md` if there's no more specific owner.
