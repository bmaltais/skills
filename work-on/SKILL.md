---
name: work-on
description: Work on another repo from the hub session. Use when the user says "work on <repo>", names a repo from the hub's Other Repos list, or starts a cross-repo task from the hub.
---

You are in the hub, not the repo. The child repo's `AGENTS.md`/`CLAUDE.md` was **not** auto-loaded, so load it yourself before touching anything.

## 1. Resolve
- Find `<repo>` in the hub `AGENTS.md` "Other Repos" list. Path is `~/StartFS/github/<repo>`; if missing, clone from the URL in that list (default `https://github.com/bmaltais/<repo>.git`).
- Not in the list: say so and ask; do not guess a path.

## 2. Orient (read, don't skim)
In parallel:
- `<repo>/AGENTS.md` and `CLAUDE.md` if present. Its rules (test commands, "never run X", branch policy) override the hub's.
- `~/StartFS/github/workbench/<repo>/README.md` and `handoff.md`, if the folder exists. Check the handoff against `git -C <repo> log --oneline -10`.
- `git -C <repo> status -sb` and `git -C <repo> worktree list`.

Then state in 3 lines: repo state, the repo's check command, what you will do. Stop and ask if the tree is dirty with work you did not make.

## 3. Isolate
Never commit to the repo's default branch. For anything beyond a one-line fix, make a worktree so the user's checkout stays untouched and other agents can work in parallel:

`git -C <repo> worktree add ../<repo>-<feature> -b <feature>`

Work in that path. Remove it after the PR merges (`git worktree remove`).

## 4. Work
- Use absolute paths and `git -C <path>`; the shell may reset to the hub between calls. Never run repo commands from the hub dir by accident (`git status` there shows the hub).
- Run the repo's own check command before every commit. Fix every warning.
- Use the repo's own tooling and skills first. For a sizeable feature, hand the work to `/grill-with-docs` → `/to-spec` → `/to-tickets` → `/implement`, pointed at the repo path.
- For independent legwork across repos, delegate per repo to subagents (see `commander`), each told its repo path and to read that repo's `AGENTS.md` first.
- Cross-repo change: one branch and one PR per repo; list the order they must merge in.

## 5. Close
- Commit on the feature branch; push and open a PR if the user asked. Do not merge your own PR.
- Anything not derivable from git or code (a decision and why, a plan, an open problem) goes in `workbench/<repo>/`, plus a line in its `log.md`; run `/workbench wrap` at session end. Never put such notes in the repo or the hub.
- If the work taught the hub something shared (a standard, a term, a decision), put it in `hub/wiki/`, on a hub branch.

## Pitfalls
- Reading only the hub's `AGENTS.md` and assuming it covers the repo. It does not.
- Editing the user's main checkout while a worktree would do.
- Duplicating a skill or doc into the repo that already lives in the hub.
