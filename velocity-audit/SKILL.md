---
name: velocity-audit
description: Audit the last 24h of development work, find the bottlenecks that slowed velocity, and propose improvements.
disable-model-invocation: true
---

Audit the development work of the last 24 hours (or the window the user names), find the **bottlenecks** that slowed it down, and propose the improvements that remove them. The loop compounds: each run starts from the last report, so a fix that landed is checked against the next day's evidence. The run is unattended; ask nothing, and record every open question in the report.

A **bottleneck** is where work waited or redid itself: the one constraint that sets the pace. Fixing a non-constraint buys nothing, so rank by minutes lost and attack the top first.

## 1. Gather

Collect the **rollout** of the window, every trace of work done:

- Sessions: `session_store_sql` on the cloud store (it adds `tool_executions`: failed and slow calls), then `source: local` for the rest. Take `turns`, `session_files`, `session_refs`.
- Git: `git log --all --since='24 hours ago'` and `git worktree list`, since a `WORKTREE=` Task works outside this tree.
- Tasks and PRs: the `AB#<id>` found in sessions and commits, read through the `ado-task` skill's `az` notes.
- The newest `sandbox/velocity-audit/*.md` before today: its proposals, and which of them landed.

Done when every session, commit and Task of the window sits in one timeline, each Task from Active to merged with its wall time.

## 2. Find the bottlenecks

Read each session of the timeline for **friction**:

- the same command or lookup run again (a retry, a rerun after a failed check or hook, a re-read of one file);
- a user correction, or a question the repo already answers (`AGENTS.md`, `CODING_STANDARDS.md`, a skill);
- time spent waiting on a human, an apply, a login or a slow check;
- work thrown away (a reverted edit, a rewritten PR description, a squashed fix-up commit).

Estimate the minutes lost from the timestamps and name the **root cause**: the missing or stale document, the slow or missing check, the script that does not exist. A symptom ("the plan failed") is not a root cause.

Done when every session has a bottleneck with its evidence (session id and turn, or commit hash) or the verdict _clean_, and the bottlenecks stand ranked by minutes lost.

## 3. Propose

For each of the top bottlenecks, and for each earlier proposal that did not land or did not move its bottleneck:

- **Fix**: one concrete edit to a named artifact: a skill, an `AGENTS.md` line, a script or check in `tools/`, a document. A document edit follows `writing-for-agents`.
- **Saving**: minutes per occurrence times occurrences.
- **Tell**: the observable that proves the fix next run (a retry that no longer appears, a hook that no longer rejects).

Done when no top bottleneck lacks a fix, and every fix names an artifact path and a tell.

## 4. Report

Write `sandbox/velocity-audit/<YYYY-MM-DD>.md` (git-ignored): the window, the timeline, the ranked bottlenecks with evidence, the proposals, the earlier proposals and their outcome. Open with the three proposals worth most.

Hand over the report path and the top three. The audit edits only its report; the user picks the proposals, and each pick becomes a Task under `ado-task`.

Done when the report file exists and the answer names it with the top three.
