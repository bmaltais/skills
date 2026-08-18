# CI Status-Checking Gotchas

Conditional branches hit while checking CI status (Section 4) or requesting a merge — not the common path, only reach for the one matching what you actually hit.

## Pager hangs on `gh pr checks`

If `gh pr checks` (with or without `--watch`) opens an alternate screen buffer and returns no usable output even with `PAGER=cat GH_PAGER=cat` — this happens in some environments and the PAGER fix does not reliably solve it. Don't retry it; switch immediately to the JSON-based equivalent, which never invokes a pager:

```bash
# Workflow run status (replaces `gh pr checks`)
gh run list --branch $(git branch --show-current) --json databaseId,name,status,conclusion | cat

# PR mergeability + per-check rollup (replaces `gh pr checks --watch`)
gh pr view <PR_NUMBER> --json state,mergeable,mergeStateStatus,statusCheckRollup \
  --jq '{state, mergeable, mergeStateStatus, checks: [.statusCheckRollup[] | {name: .name, status: .status, conclusion: .conclusion}]}' | cat
```

Poll the second command in a loop instead of `--watch` if you need to wait for checks to finish.

## `action_required` on workflow-file changes

Newly added/modified workflow files may show `action_required`. If the PR itself adds or edits files under `.github/workflows/`, GitHub can mark those runs `action_required` (empty job list, no logs) even for the PR author with write access — this isn't a fork-only restriction. Approve them directly:

```bash
gh run list --branch $(git branch --show-current) --json databaseId,conclusion --jq '.[] | select(.conclusion=="action_required") | .databaseId' \
  | xargs -I{} gh api --method POST repos/$OWNER/$REPO/actions/runs/{}/approve
```

This can recur on **every** push that still touches a workflow file — re-check `gh run list` after each push, not just the first.

## `action_required` on a bot-authored commit (403 on approve)

`action_required` on a commit authored by a bot/app identity (e.g. the Copilot coding agent) can 403 on the approve endpoint — `gh api --method POST .../actions/runs/{id}/approve` returns `"This run is not from a fork pull request or queued by the Actions bot"` even though `gh run list` shows `action_required`. This gate isn't the fork-PR-approval one the endpoint covers, so don't keep retrying it. Instead, as a repo collaborator with write access, re-trigger the run directly — it re-evaluates under your own permissions rather than the bot's, and typically completes with no UI step at all:

```bash
gh run rerun <RUN_ID>
```

Only fall back to telling the user it needs a manual **Approve and run workflows** click in the Actions tab UI if the rerun itself comes back `action_required` again.

**This can cascade when the repo also has an auto-committing workflow** (see below). A successful rerun can let that workflow push a *new* commit (e.g. a `terraform-docs` regeneration triggered by content that actually changed) — that new commit is itself bot-authored, so it lands with its own fresh pair of `action_required` runs needing another `gh run rerun` round. Don't stop after one successful rerun cycle: re-check `gh run list` after each rerun, and only consider CI settled once it reports all-green with no new commits on `git fetch`.

## Branch gains a commit from an auto-committing workflow

If the repo has a workflow that auto-commits back to your branch (e.g. a docs-generation workflow with `git-push: "true"`, common alongside `terraform-docs/gh-actions`), expect the remote branch to gain a commit shortly after your push completes. A second `git push` for a follow-up fix will then be rejected as non-fast-forward. Always `git fetch origin <branch>` and `git rebase origin/<branch>` before pushing again — don't assume you're the only writer to the branch:

```bash
git fetch origin $(git branch --show-current)
git rebase origin/$(git branch --show-current)
git push
```

## Repos with Projects (classic) break `gh pr edit` and `gh pr view`

Any `gh pr` subcommand that queries `projectCards` — including `gh pr edit` and `gh pr view` (with or without `--comments`) — exits non-zero printing `GraphQL: Projects (classic) is being deprecated in favor of the new Projects experience`. The command fails even though the deprecation is a warning, not an error — a known `gh` CLI bug. Bypass GraphQL entirely with REST via `gh api`:

```bash
# Update title/body instead of `gh pr edit`
gh api --method PATCH repos/$OWNER/$REPO/pulls/N -f title="..." -f body="..." --jq '.html_url'

# Read PR reviews, review comments, and issue/PR comments instead of `gh pr view --comments`
gh api repos/$OWNER/$REPO/pulls/N/reviews
gh api repos/$OWNER/$REPO/pulls/N/comments
gh api repos/$OWNER/$REPO/issues/N/comments
```
