---
name: github-pr-workflow
description: Use when the user wants to create a branch, open or update a pull request, check or poll CI status, auto-fix a failing CI run, or merge a PR. Full lifecycle via gh CLI, with a git + GitHub REST API (curl) fallback for machines without gh.
categories: [github]
agents: [pi, hermes, claude, copilot]
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  source: custom
  scope: global
  hermes:
    tags: [GitHub, Pull-Requests, CI/CD, Git, Automation, Merge]
    related_skills: [github-auth, github-code-review]
---

# GitHub Pull Request Workflow

Complete guide for managing the PR lifecycle, written for the `gh` CLI path. If Quick Auth Detection below sets `AUTH="git"` (no `gh` available), every gh command in this file has a one-to-one `curl` equivalent in [`references/git-curl-fallback.md`](references/git-curl-fallback.md) — same section numbers, same order.

## Prerequisites

- Authenticated with GitHub (see `github-auth` skill)
- Inside a git repository with a GitHub remote

### Quick Auth Detection

```bash
# Determine which method to use throughout this workflow
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  # Ensure we have a token for API calls
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi
echo "Using: $AUTH"
```

If `AUTH="git"`, also run the owner/repo extraction at the top of [`references/git-curl-fallback.md`](references/git-curl-fallback.md) — every curl command there needs it.

---

## 1. Branch Creation

**Before branching, check for an already-open, unmerged PR from earlier in this session** (`gh pr list --state open --json number,headRefName,title`). If this request adds to or fixes something in that PR's scope, commit to its existing branch instead of opening a new one — only branch fresh when the user explicitly asks for a separate PR, or the change is genuinely unrelated. Opening a second PR for related, still-in-flight work creates duplicate review surface and requires closing one afterward.

**If reusing an existing branch instead of creating a new one** (e.g. continuing work from an earlier session), run `git fetch origin && git merge-base HEAD origin/<base>` before your first commit — the branch can look up-to-date locally while `origin/<base>` has already merged unrelated work since it was last fetched, and pushing without catching this silently reintroduces stale state into the PR.

This part is pure `git` — identical either way:

```bash
# Make sure you're up to date
git fetch origin
git checkout main && git pull origin main

# Create and switch to a new branch
git checkout -b feat/add-user-authentication
```

Branch naming conventions:
- `feat/description` — new features
- `fix/description` — bug fixes
- `refactor/description` — code restructuring
- `docs/description` — documentation
- `ci/description` — CI/CD changes

## 2. Making Commits

Use the agent's file tools (`write_file`, `patch`) to make changes, then commit:

```bash
# Stage specific files
git add src/auth.py src/models/user.py tests/test_auth.py

# Commit with a conventional commit message
git commit -m "feat: add JWT-based user authentication

- Add login/register endpoints
- Add User model with password hashing
- Add auth middleware for protected routes
- Add unit tests for auth flow"
```

> **Before `git add -A`, run `git status` and check for changes/deletions you didn't make.** A workspace can already have unrelated modifications (stale deletions, another in-progress edit) predating your task. Staging everything indiscriminately ships them in your PR. Restore anything out of scope with `git checkout -- <path>` (or stage only the files your task actually touched) before committing.

Commit message format: [Conventional Commits](references/conventional-commits.md) — types, scope, breaking changes, multi-line bodies, issue linking, and the `-F`-over-`-m` shell-escaping fix for `!`/backtick/`$` characters.

## 3. Pushing and Creating a PR

### Push the Branch (same either way)

```bash
git push -u origin HEAD
```

### Create the PR

**With gh:**

```bash
gh pr create \
  --title "feat: add JWT-based user authentication" \
  --body "## Summary
- Adds login and register API endpoints
- JWT token generation and validation

## Test Plan
- [ ] Unit tests pass

Closes #42"
```

Options: `--draft`, `--reviewer user1,user2`, `--label "enhancement"`, `--base develop`

> **Tip: avoid inline `--body` for long or backtick-heavy descriptions.** Escaping nested backticks/quotes inside a shell `--body "..."` argument is error-prone (a single stray quote silently truncates or corrupts the body). Write the body to a temp file and use `--body-file`:
> ```bash
> cat > /tmp/pr-body.md <<'EOF'
> ## Summary
> - Uses `backticks` and "quotes" freely — heredoc needs no escaping
> EOF
> gh pr create --title "..." --body-file /tmp/pr-body.md
> ```
> If a body already went out malformed, fix it with `gh api --method PATCH repos/OWNER/REPO/pulls/N -f body="$(cat /tmp/pr-body.md)"` rather than re-running `gh pr create`.

For the `--body-file` content itself, start from [`templates/pr-body-feature.md`](templates/pr-body-feature.md) or [`templates/pr-body-bugfix.md`](templates/pr-body-bugfix.md) rather than freehanding the sections.

Without `gh`: see [`references/git-curl-fallback.md`](references/git-curl-fallback.md) § Section 3 for the curl equivalent.

### Reading a Reviewer's Feedback

**A reviewer's own fix commit plus its own test asserting that fix is not independent verification.** Before building further work on top of it, check any factual claim the review makes about an external system (an API constraint, a provider default, a library behavior) against a primary source — the test only proves the fix is internally consistent with the reviewer's assumption, not that the assumption is correct.

Once the reviewer posts its findings, fetch them with `gh api` — reaching for `gh pr view --comments` first hits the same Projects (classic) GraphQL error as `gh pr edit`; see [`references/ci-status-gotchas.md`](references/ci-status-gotchas.md) for the working `gh api` calls (issue comments, reviews, review comments).

## 4. Monitoring CI Status

### Check CI Status

**With gh:**

```bash
# Try this first (works in most environments):
PAGER=cat GH_PAGER=cat gh pr checks
```

> **Hit a pager hang, an `action_required` check, a rejected push on a follow-up fix, or a Projects (classic) GraphQL error on `gh pr edit`/`gh pr view`?** These are environment/repo-specific branches, not the common path — see [`references/ci-status-gotchas.md`](references/ci-status-gotchas.md).

Without `gh`: see [`references/git-curl-fallback.md`](references/git-curl-fallback.md) § Section 4 for the status query, check-runs query, and poll-until-complete loop.

## 5. Auto-Fixing CI Failures

When CI fails, diagnose and fix. This loop works with either auth method.

### Step 1: Get Failure Details

**With gh:**

```bash
# List recent workflow runs on this branch
gh run list --branch $(git branch --show-current) --limit 5

# View failed logs
gh run view <RUN_ID> --log-failed
```

Without `gh`: see [`references/git-curl-fallback.md`](references/git-curl-fallback.md) § Section 5 for listing workflow runs via curl.

Once you have a `RUN_ID`, download and read its logs, then match the failure against a known pattern — see [`references/ci-troubleshooting.md`](references/ci-troubleshooting.md) for the log-download command and the diagnosis/fix table for test, lint, type-check, build, permission, timeout, and Docker failures.

### Step 2: Fix and Push

After identifying the issue, use file tools (`patch`, `write_file`) to fix it:

```bash
git add <fixed_files>
git commit -m "fix: resolve CI failure in <check_name>"
git push
```

### Step 3: Verify

Re-check CI status using the commands from Section 4 above.

### Auto-Fix Loop Pattern

When asked to auto-fix CI, follow this loop:

1. Check CI status → identify failures
2. Read failure logs → understand the error
3. Use `read_file` + `patch`/`write_file` → fix the code
4. `git add . && git commit -m "fix: ..." && git push`
5. Wait for CI → re-check status
6. Repeat if still failing (up to 3 attempts, then ask the user)

## 6. Merging

**With gh:**

```bash
# Squash merge + delete branch (cleanest for feature branches)
gh pr merge --squash --delete-branch

# Enable auto-merge (merges when all checks pass)
gh pr merge --auto --squash --delete-branch
```

Merge methods: `"merge"` (merge commit), `"squash"`, `"rebase"`

Without `gh`: see [`references/git-curl-fallback.md`](references/git-curl-fallback.md) § Section 6 for merging and enabling auto-merge via curl/GraphQL.

## Useful PR Commands Reference

| Action | gh |
|--------|-----|
| List my PRs | `gh pr list --author @me` |
| View PR diff | `gh pr diff` |
| Add comment | `gh pr comment N --body "..."` |
| Read review feedback | `gh api repos/OWNER/REPO/issues/N/comments` — see "Reading the Review's Feedback" above |
| Request review | `gh pr edit N --add-reviewer user` |
| **Update title/body** | `gh pr edit N --title "..." --body "..."` ⚠️ see [`references/ci-status-gotchas.md`](references/ci-status-gotchas.md) if the repo has Projects (classic) |
| Close PR | `gh pr close N` |
| Check out someone's PR | `gh pr checkout N` |

Without `gh`: see [`references/git-curl-fallback.md`](references/git-curl-fallback.md) § Other PR Actions for the curl equivalent of every row above.
