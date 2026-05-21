---
name: git-proxy
description: Safe git operations — commits, pushes, branches, merges, and rebases with safety constraints enforced.
categories: [software-development]
agents: [pi, hermes, claude, copilot]
version: 2026-01-01
triggers: ["commit", "push", "branch", "merge", "rebase", "pull request", "PR"]
tools: [bash]
preconditions: [".git exists"]
constraints: ["never force push to main", "never force push to protected branches", "run tests before push"]
metadata:
  source: custom
  scope: global
---

# Git Proxy — all git operations with a safety net

Handle git operations consistently. The fences (`constraints` above) are
enforced by the `pre_tool_call` hook; this file tells the agent what good
behavior looks like within those fences.

## Commit
- Stage specific files, not `git add -A` (avoids capturing secrets).
- Write messages that explain *why*, not *what*.
- Reference the task or issue if one exists.

## Push
- **Pull before you commit to any shared repo** (including skills repos like
  `~/.copilot/skills`, `~/.claude/skills`, `~/.hermes/skills`). Run
  `git pull --rebase` first; if it fails due to unstaged changes, stash
  first (`git stash && git pull --rebase && git stash pop`). A push rejection
  after a commit is much harder to recover from than a pre-commit pull.
- Run tests first. If tests aren't present, say so explicitly.
- Never force-push to a protected branch. The pre-call hook will block this
  even if you try.
- Prefer `--force-with-lease` over `--force` on feature branches.

## Diverged branch recovery
When a push is rejected because local and remote have diverged:
1. Check what you have: `git log --oneline origin/HEAD..HEAD` (your commits)
   and `git log --oneline HEAD..origin/HEAD` (remote-only commits).
2. If your commits are small and isolated, prefer **rebase**:
   `git fetch origin && git rebase origin/main`. Resolve conflicts, then push.
3. **Do NOT use `git reset --hard origin/main`** to "start over" — if your
   commits added new tracked files, the hard reset will delete them from the
   working tree. Use `git stash` (or copy the files elsewhere) before any
   hard reset if you need to keep new files.
4. After a successful rebase/merge, push normally.

## Branch / merge / rebase
- Rebase feature branches on `main` before opening a PR.
- Resolve conflicts manually; do not `-X theirs` or `-X ours` without thinking.
- Merge via PR with review, not directly on the command line.

## Self-rewrite hook
After every 5 uses, re-read `KNOWLEDGE.md` and the last 10 git-proxy
episodic entries. If a new failure mode has appeared, append a heuristic
to `KNOWLEDGE.md`. If a constraint was violated, escalate to `LESSONS.md`.
