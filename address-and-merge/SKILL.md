---
name: address-and-merge
description: Address all review feedback on an open PR, merge it, and clean up the branch. Use when the user says "address the feedback on PR N", "fix the review comments", "merge PR N", "address and merge", or "clean up after merging". Handles inline (line-level) and conversation-level review comments, runs the build/test suite, commits the fixes, pushes, squash-merges the PR, deletes the remote branch, deletes the local branch, and returns to main.
---

# Address and Merge

A complete end-to-end workflow that takes an open PR from "has review comments"
to "merged and cleaned up". Handles both automated (Copilot) inline comments and
human conversation comments, verifies the build, and leaves the repo on a clean
main branch.

## Invocation

```
/address-and-merge          — detect the current branch's open PR automatically
/address-and-merge #N       — go straight to PR N
```

## Phase 1 — Identify the PR

If a PR number was given, use it directly.

If no number was given, detect the PR for the current branch:

```bash
gh pr view --json number,title,headRefName,state
```

If the branch has no associated PR, or the PR is already merged/closed, stop and
tell the user.

Make sure the local branch is checked out and up to date:

```bash
git checkout <branch>
git pull
```

## Phase 2 — Fetch All Review Comments

Fetch **both** comment types — they come from different API endpoints.

```bash
# 1. Inline review comments (line-level — Copilot automated review lives here)
gh api repos/{owner}/{repo}/pulls/{N}/comments \
  --jq '.[] | {id: .id, path: .path, line: .line, body: .body}'

# 2. Conversation-level comments (general PR discussion)
gh pr view {N} --comments --json comments \
  --jq '.comments[] | {author: .author.login, body: .body}'
```

> **Important:** `gh pr view --comments` does NOT return inline review comments.
> They are two separate endpoints. Always fetch both.

If there are no unresolved comments of either type, skip to Phase 4 (merge).

## Phase 3 — Address Each Comment

Work through comments one at a time:

1. **Locate the code** — use `path` + `line` from inline comments, or search the
   codebase for the relevant symbol/pattern from conversation comments.

2. **Understand the fix** — read the surrounding context before editing. If the
   comment is ambiguous, make the most reasonable interpretation and note it in
   the commit message.

3. **Apply the fix** — edit the file directly using the edit tool. Never use
   `sed`, `awk`, or bash string manipulation to modify source code.

4. **Repeat** for all comments before running the build.

### Common fix categories

| Comment type | Typical fix |
|---|---|
| Magic literal → named constant | Replace literal with existing constant in same package |
| Missing counter increment | Add `counter++` in the matching error/success branch |
| Doc comment inaccuracy | Rewrite the doc comment to match actual behaviour |
| Unused import / wrong import | Swap or remove the import |
| Error silently swallowed | Add error logging or propagation |

## Phase 4 — Verify

After all fixes are applied:

```bash
go build ./...
go test ./...
go vet ./...
```

(Substitute the project's actual build/test commands if different — check
`Makefile`, `AGENTS.md`, or `README.md` for the canonical commands.)

Fix any errors before proceeding. Do not suppress or ignore failures.

## Phase 5 — Commit and Push

```bash
git add <changed files>
git commit -m "fix: address PR #N review feedback (<brief summary of fixes>)"
git push
```

Use a single commit for all review fixes. The commit message should name the PR
number and give a short parenthetical summary of what was fixed, e.g.:

```
fix: address PR #70 review feedback (NoOptDefVal constant, errCount on merge error)
```

## Phase 6 — Merge

Squash-merge the PR so the feature lands as a single commit on main:

```bash
gh pr merge {N} --squash
```

If the command fails with "Pull Request is not mergeable", check the actual merge state:

```bash
gh pr view {N} --json mergeStateStatus,mergeable,state
```

If `mergeable` is `MERGEABLE` and `mergeStateStatus` is `CLEAN`, GitHub's API
had a transient inconsistency after the push. Wait 3–5 seconds and retry:

```bash
sleep 5 && gh pr merge {N} --squash
```

Wait for the merge to complete before proceeding.

## Phase 7 — Clean Up

Delete the remote branch, then the local branch, then return to main:

```bash
# Delete remote branch
git push origin --delete <branch>

# Return to main and pull
git checkout main
git pull

# Delete local branch (use -D because squash merge means git won't see it as
# fully merged via the standard ancestor check)
git branch -D <branch>
```

> **Note on `-D` vs `-d`:** After a squash merge, the local branch tip is not an
> ancestor of main (the squash commit has a different SHA). Use `-D` to force-
> delete. This is safe — the code is on main.

## Phase 8 — Report

Confirm to the user:

```
PR #N merged ✓
Branch <branch> deleted (remote + local) ✓
Now on main @ <short SHA>
```

## Key Invariants

- NEVER force-push over an existing review — always add a new commit
- NEVER merge before the build and tests pass
- NEVER leave the remote branch alive after a successful merge
- ALWAYS use `--squash` for merge to keep main history linear
- ALWAYS use `-D` (not `-d`) to delete the local branch after a squash merge
- ALWAYS fetch both inline (`gh api .../pulls/{N}/comments`) and conversation
  (`gh pr view {N} --comments`) comment types — they are different endpoints
