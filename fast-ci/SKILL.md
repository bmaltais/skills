---
name: fast-ci
description: Cut a repo's CI to a 2-minute median and 3-minute p95 without hiding failures, one measured PR per change.
disable-model-invocation: true
---

Make CI as fast as possible while it stays **honest**: every speedup keeps every failure visible. Target: a PR gets its result in under 2 minutes at the median and under 3 at p95.

Two rules outrank speed:

- **Merge queue runs the full suite** before anything reaches main. Selection only narrows PR feedback.
- **A check that needs a retry has a bug.** Find the bug. Retries, wider timeouts and skipped tests are all forms of hiding.

## 1. Audit

Pull the last 150 runs. Split every job into **waiting**, **setup** and **running**, at p50 and p95.

Done when the table covers every job and the biggest bucket is named. Fix that bucket first; it is rarely the tests, so leave them standing.

## 2. Hit the budgets

Take the budgets in the table below in the order the audit ranks them. The tools are defaults: keep an old one only for a measured reason, and take anything newer that is faster on this repo. Before each switch, run old and new side by side and list what the new one misses.

| Bucket | Budget | Move |
| --- | --- | --- |
| Waiting | < 10 s | Every job on Blacksmith, the 5-second ones too (a 5-second job that queues 10 minutes is a 10-minute job). Cancel a branch's in-progress run when a new commit lands. |
| Setup | < 30 s | PR cache hits above 95%, caches seeded from main. Cache `node_modules` itself, not just the package cache. Blobless clone (`filter: blob:none`) in place of a shallow one. |
| Lint | < 5 s | oxlint, every rule you can turn on. Delete ESLint. |
| Typecheck | < 5 s | `bun check`; TypeScript 7 when it cannot check this repo; tsrs locally. |
| Format | | oxfmt. Delete Prettier. |
| Install, scripts | | bun. Delete npm, yarn, pnpm. |
| Tests | < 60 s per shard | Vitest `isolate: false` (no app reload per test file), state reset after every file with the cleanup rules written into AGENTS.md, random order to flush out leaks. Shard by measured duration onto 8-core machines, each with its own database. Buy cores before shards; concurrency equals cores. |
| Shape | | Lint, typecheck, build and tests in parallel. Then move migration checks and other apps' tests out of the slowest job into their own. |
| Selection | | On PRs, run what the diff can reach (`nx affected`, `turbo --affected`). Then hide a real change from it on purpose: CI must go red. |
| Local | < 9 s | A pre-push hook running format, lint and typecheck on changed files. A hook, because agents skip a line in AGENTS.md. |
| Guard | | Any job over its budget fails. |

Done when each row is met or has a measured reason it cannot be, written in the PR body.

## 3. Ship

One small PR per change, with before and after numbers from real runs.

Do everything that needs no human first. Collect what needs an account, a secret or a bigger bill into one list with the expected monthly cost, and bring that list at the end.

Done when the last PR is merged and the report ends with total CI time and cost, before and after.
